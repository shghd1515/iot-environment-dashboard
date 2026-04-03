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

# 텔레그램 설정
TELEGRAM_TOKEN   = "8741549548:AAEb0QB0F1CRoLkIp3waEEfODcpsUqyu_OE"
TELEGRAM_CHAT_ID = "8717882823"

def send_telegram(message: str):
    """텔레그램 알림 전송"""
    try:
        requests.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": TELEGRAM_CHAT_ID, "text": message},
            timeout=5
        )
        print(f"[텔레그램] 알림 전송: {message}")
    except Exception as e:
        print(f"[텔레그램 오류] {e}")

# 이전 값 저장용
prev_values = {"temp": None, "humi": None, "pm25": None}

def detect_anomaly(curr_temp, curr_humi, curr_pm25):
    """이상치 감지 및 알림"""
    global prev_values

    alerts = []

    if prev_values["pm25"] is not None and prev_values["pm25"] > 0:
        pm25_change = (curr_pm25 - prev_values["pm25"]) / prev_values["pm25"] * 100
        if pm25_change >= 50:
            alerts.append(
                f"🚨 미세먼지 급등 감지!\n"
                f"PM2.5: {prev_values['pm25']} → {curr_pm25} μg/m³ (+{pm25_change:.0f}%)\n"
                f"원인: 요리·청소·외부 유입 가능성"
            )

    if prev_values["temp"] is not None:
        temp_change = abs(curr_temp - prev_values["temp"])
        if temp_change >= 3:
            direction = "상승" if curr_temp > prev_values["temp"] else "하강"
            alerts.append(
                f"🌡️ 온도 급변 감지!\n"
                f"온도: {prev_values['temp']}°C → {curr_temp}°C ({direction} {temp_change:.1f}°C)"
            )

    if prev_values["humi"] is not None:
        humi_change = abs(curr_humi - prev_values["humi"])
        if humi_change >= 10:
            direction = "상승" if curr_humi > prev_values["humi"] else "하강"
            alerts.append(
                f"💧 습도 급변 감지!\n"
                f"습도: {prev_values['humi']}% → {curr_humi}% ({direction} {humi_change:.1f}%)"
            )

    for alert in alerts:
        msg = f"{alert}\n대시보드: https://iot-environment-dashboard.onrender.com"
        send_telegram(msg)
        print(f"[이상치 감지] {alert}")
        try:
            with engine.connect() as conn:
                conn.execute(text(
                    "UPDATE sensor_combined SET event = :e "
                    "WHERE recorded_at = (SELECT MAX(recorded_at) FROM "
                    "(SELECT recorded_at FROM sensor_combined) AS t)"
                ), {"e": "이상치감지"})
                conn.commit()
        except Exception as e:
            print(f"[이상치 DB 오류] {e}")

    prev_values["temp"] = curr_temp
    prev_values["humi"] = curr_humi
    prev_values["pm25"] = curr_pm25

# ── DB 연결 ───────────────────────────────────────────────────────────────────
def get_engine():
    supabase_url = os.getenv("SUPABASE_DB_URL")
    if supabase_url:
        return create_engine(supabase_url, pool_pre_ping=True)
    url = (
        f"mysql+pymysql://{os.getenv('DB_USER','root01')}:{os.getenv('DB_PASSWORD','00000')}"
        f"@{os.getenv('DB_HOST','192.168.101.2')}:{os.getenv('DB_PORT','3307')}"
        f"/{os.getenv('DB_NAME','sensor_db')}?charset=utf8mb4"
    )
    return create_engine(url, pool_pre_ping=True)

engine = get_engine()

CREATE_LOG_TABLE = """
CREATE TABLE IF NOT EXISTS control_log (
    id              SERIAL PRIMARY KEY,
    logged_at       TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    hour_of_day     SMALLINT,
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
    # 텔레그램 알림 추가
    send_telegram(
        "🪟 환기 알림!\n"
        "지금 창문을 열어 15분간 환기하세요!\n"
        f"대시보드: https://iot-environment-dashboard.onrender.com"
    )
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
    # 텔레그램 알림 추가
    send_telegram(
        "🪟 환기 종료 알림!\n"
        "15분간 환기 완료! 창문을 닫으세요.\n"
        f"대시보드: https://iot-environment-dashboard.onrender.com"
    )
    try:
        requests.post(f"{API_BASE}/event",
                      json={"event_name": "환기종료"}, timeout=5)
        print("[이벤트] 환기종료 DB 기록 완료")
    except Exception as e:
        print(f"[이벤트 오류] {e}")

def weekly_report():
    """매주 일요일 저녁 8시 주간 리포트 텔레그램 발송"""
    print("[주간 리포트] 생성 중...")
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT
                    ROUND(AVG(temperature)::numeric, 1) as avg_temp,
                    ROUND(MIN(temperature)::numeric, 1) as min_temp,
                    ROUND(MAX(temperature)::numeric, 1) as max_temp,
                    ROUND(AVG(humidity)::numeric, 1)    as avg_humi,
                    ROUND(AVG(pm25)::numeric, 1)        as avg_pm25,
                    ROUND(MAX(pm25)::numeric, 1)        as max_pm25,
                    COUNT(*) as total,
                    COUNT(CASE WHEN event IS NOT NULL THEN 1 END) as event_count
                FROM sensor_combined
                WHERE recorded_at >= NOW() - INTERVAL '7 days'
            """)).fetchone()

        if result:
            pm25_grade = "좋음" if result[4] < 15 else "보통" if result[4] < 35 else "나쁨"
            msg = (
                f"📊 주간 환경 리포트\n"
                f"{'='*25}\n"
                f"📅 기간: 최근 7일\n\n"
                f"🌡️ 온도\n"
                f"  평균: {result[0]}°C\n"
                f"  최저: {result[1]}°C / 최고: {result[2]}°C\n\n"
                f"💧 습도\n"
                f"  평균: {result[3]}%\n\n"
                f"🌫️ 미세먼지 (PM2.5)\n"
                f"  평균: {result[4]} μg/m³ ({pm25_grade})\n"
                f"  최고: {result[5]} μg/m³\n\n"
                f"📝 수집 데이터: {result[6]:,}개\n"
                f"🔔 이벤트 기록: {result[7]}회\n\n"
                f"대시보드: https://iot-environment-dashboard.onrender.com"
            )
            send_telegram(msg)
            print("[주간 리포트] 전송 완료")
    except Exception as e:
        print(f"[주간 리포트 오류] {e}")

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

        # ── 이상치 감지 ──────────────────────────────
        detect_anomaly(curr_temp, curr_humi, curr_pm25)
        # 텔레그램 알림 조건
        if curr_pm25 >= 35:
            send_telegram(
                f"🚨 미세먼지 경보!\n"
                f"PM2.5: {curr_pm25} μg/m³ (나쁨 이상)\n"
                f"현재 온도: {curr_temp}°C / 습도: {curr_humi}%\n"
                f"대시보드: https://iot-environment-dashboard.onrender.com"
            )
        if curr_temp >= 28:
            send_telegram(
                f"🌡️ 온도 높음 경보!\n"
                f"현재 온도: {curr_temp}°C\n"
                f"대시보드: https://iot-environment-dashboard.onrender.com"
            )
        if curr_temp <= 15:
            send_telegram(
                f"🥶 온도 낮음 경보!\n"
                f"현재 온도: {curr_temp}°C\n"
                f"대시보드: https://iot-environment-dashboard.onrender.com"
            )
        if curr_humi >= 70:
            send_telegram(
                f"💧 습도 높음 경보!\n"
                f"현재 습도: {curr_humi}%\n"
                f"대시보드: https://iot-environment-dashboard.onrender.com"
            )
        if curr_humi <= 30:
            send_telegram(
                f"🏜️ 습도 낮음 경보!\n"
                f"현재 습도: {curr_humi}%\n"
                f"대시보드: https://iot-environment-dashboard.onrender.com"
            )

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

    # 매주 일요일 저녁 8시 주간 리포트
    scheduler.add_job(weekly_report, "cron",
                      day_of_week="sun", hour=20, minute=0,
                      id="weekly_report")
    
    try:
        scheduler.start()
    except KeyboardInterrupt:
        print("\n스케줄러 종료")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
