"""
05_auto_scheduler.py
매 분마다 FastAPI에서 현재 센서값 + 권장값을 받아
자동 제어 로그를 DB에 기록하는 스케줄러

변경사항:
  - DB: 노트북 MariaDB (port 3307, root01)
  - PM2.5 제어 판단 추가
  - 오후 2시 환기 알람 (콘솔 + 소리)
  - sensor_combined 테이블 기반

실행:
    pip install apscheduler requests python-dotenv sqlalchemy pymysql
    python 05_auto_scheduler.py
"""

import os
import time
import requests
from datetime import datetime
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from apscheduler.schedulers.blocking import BlockingScheduler

load_dotenv()

API_BASE           = os.getenv("API_BASE", "http://localhost:8000")
CHECK_INTERVAL_MIN = 1


# ── DB 연결 ───────────────────────────────────────────────────────────────────
def get_engine():
    url = (
        f"mysql+pymysql://{os.getenv('DB_USER','root01')}:{os.getenv('DB_PASSWORD','00000')}"
        f"@{os.getenv('DB_HOST','192.168.101.2')}:{os.getenv('DB_PORT','3307')}"
        f"/{os.getenv('DB_NAME','sensor_db')}?charset=utf8mb4"
    )
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

CREATE_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS control_log (
    id              INT AUTO_INCREMENT PRIMARY KEY,
    logged_at       DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
    hour_of_day     TINYINT  NOT NULL,
    current_temp    FLOAT,
    current_humi    FLOAT,
    current_pm25    FLOAT,
    target_temp     FLOAT,
    target_humidity FLOAT,
    target_pm25     FLOAT,
    temp_diff       FLOAT,
    humi_diff       FLOAT,
    pm25_diff       FLOAT,
    action          VARCHAR(200)
)
"""

def init_log_table():
    with engine.connect() as conn:
        conn.execute(text(CREATE_LOG_TABLE))
        conn.commit()
    print("[DB] control_log 테이블 준비 완료")


def log_control(data: dict):
    sql = """
        INSERT INTO control_log
            (hour_of_day, current_temp, current_humi, current_pm25,
             target_temp, target_humidity, target_pm25,
             temp_diff, humi_diff, pm25_diff, action)
        VALUES
            (:hour, :curr_temp, :curr_humi, :curr_pm25,
             :target_temp, :target_humi, :target_pm25,
             :temp_diff, :humi_diff, :pm25_diff, :action)
    """
    with engine.connect() as conn:
        conn.execute(text(sql), data)
        conn.commit()


# ── 장치 제어 판단 ────────────────────────────────────────────────────────────
def control_device(curr_temp, tgt_temp, curr_humi, tgt_humi,
                   curr_pm25, tgt_pm25) -> str:
    actions = []

    temp_diff = tgt_temp - curr_temp
    humi_diff = tgt_humi - curr_humi
    pm25_diff = curr_pm25 - tgt_pm25   # 현재가 목표보다 높으면 양수

    if temp_diff > 1.0:
        actions.append(f"히터 ON (+{temp_diff:.1f}°C)")
    elif temp_diff < -1.0:
        actions.append(f"냉방 ON ({temp_diff:.1f}°C)")
    else:
        actions.append("온도 유지")

    if humi_diff > 3.0:
        actions.append(f"가습기 ON (+{humi_diff:.1f}%)")
    elif humi_diff < -3.0:
        actions.append(f"제습기 ON ({humi_diff:.1f}%)")
    else:
        actions.append("습도 유지")

    # 미세먼지 경보
    if curr_pm25 >= 75:
        actions.append(f"미세먼지 매우나쁨! PM2.5={curr_pm25} - 공기청정기 최강")
    elif curr_pm25 >= 35:
        actions.append(f"미세먼지 나쁨 PM2.5={curr_pm25} - 공기청정기 가동")
    elif curr_pm25 >= 15:
        actions.append(f"미세먼지 보통 PM2.5={curr_pm25}")
    else:
        actions.append(f"미세먼지 좋음 PM2.5={curr_pm25}")

    return " | ".join(actions)


# ── 오후 2시 환기 알람 ────────────────────────────────────────────────────────
def ventilation_alarm():
    print("\n" + "🔔 "*20)
    print("★ 오후 2시입니다! 지금 창문을 열어 15분간 환기하세요! ★")
    print("🔔 "*20 + "\n")

    # FastAPI로 이벤트 기록 요청
    try:
        requests.post(f"{API_BASE}/event",
                      json={"event_name": "환기시작"}, timeout=5)
        print("[이벤트] 환기시작 DB 기록 완료")
    except Exception as e:
        print(f"[이벤트 오류] {e}")


def ventilation_end():
    print("\n" + "="*50)
    print("★ 15분 환기 완료! 창문을 닫으세요. ★")
    print("="*50 + "\n")
    try:
        requests.post(f"{API_BASE}/event",
                      json={"event_name": "환기종료"}, timeout=5)
        print("[이벤트] 환기종료 DB 기록 완료")
    except Exception as e:
        print(f"[이벤트 오류] {e}")


# ── 핵심 작업: 매 분 실행 ─────────────────────────────────────────────────────
def auto_control_job():
    now = datetime.now()
    print(f"\n[{now.strftime('%Y-%m-%d %H:%M:%S')}] 자동 제어 체크")

    try:
        resp = requests.get(f"{API_BASE}/status", timeout=5)
        resp.raise_for_status()
        data = resp.json()

        current = data["current"]
        rec     = data["recommendation"]
        diff    = data["diff"]

        curr_temp = current.get("temperature", 0)
        curr_humi = current.get("humidity", 0)
        curr_pm25 = current.get("pm25", 0) or 0
        tgt_temp  = rec["temperature"]
        tgt_humi  = rec["humidity"]
        tgt_pm25  = rec.get("pm25", 20)

        print(f"  현재: 온도 {curr_temp}°C / 습도 {curr_humi}% / PM2.5 {curr_pm25}μg/m³")
        print(f"  목표: 온도 {tgt_temp}°C / 습도 {tgt_humi}% / PM2.5 {tgt_pm25}μg/m³")

        action = control_device(curr_temp, tgt_temp, curr_humi, tgt_humi,
                                curr_pm25, tgt_pm25)
        print(f"  조치: {action}")

        log_control({
            "hour":       now.hour,
            "curr_temp":  curr_temp,
            "curr_humi":  curr_humi,
            "curr_pm25":  curr_pm25,
            "target_temp": tgt_temp,
            "target_humi": tgt_humi,
            "target_pm25": tgt_pm25,
            "temp_diff":  diff.get("temp_diff", 0),
            "humi_diff":  diff.get("humi_diff", 0),
            "pm25_diff":  diff.get("pm25_diff", 0),
            "action":     action,
        })

    except requests.exceptions.ConnectionError:
        print(f"  [오류] FastAPI 서버 연결 불가 ({API_BASE})")
    except Exception as e:
        print(f"  [오류] {e}")


# ── 메인 ─────────────────────────────────────────────────────────────────────
def main():
    print("===== 자동제어 스케줄러 시작 =====")
    print(f"  API 주소: {API_BASE}")
    print(f"  실행 주기: {CHECK_INTERVAL_MIN}분마다")
    print(f"  환기 알람: 매일 오후 2시 (15분)")
    print("  종료: Ctrl+C\n")

    init_log_table()
    auto_control_job()

    scheduler = BlockingScheduler()

    # 매 분 자동 제어
    scheduler.add_job(auto_control_job, "interval",
                      minutes=CHECK_INTERVAL_MIN, id="auto_control")

    # 매일 오후 2시 환기 알람
    scheduler.add_job(ventilation_alarm, "cron",
                      hour=14, minute=0, id="ventilation_start")

    # 매일 오후 2시 15분 환기 종료
    scheduler.add_job(ventilation_end, "cron",
                      hour=14, minute=15, id="ventilation_end")

    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n스케줄러 종료")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
