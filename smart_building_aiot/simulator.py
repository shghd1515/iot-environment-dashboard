# simulator.py
# ================================================
# 라즈베리파이 없이 PC에서 테스트하는 시뮬레이터
# 실제 센서 대신 현실적인 가상 데이터를 생성해
# DB 저장 파이프라인 전체를 테스트할 수 있습니다
#
# 실행: python simulator.py
# ================================================

import os
import sys
import time
import math
import random
import logging
import schedule
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.settings import (
    DB_PATH, COLLECT_INTERVAL_SEC, LOCATION_ID,
    LOG_DIR, LOG_FILE,
    TEMP_LOW_THRESHOLD, TEMP_HIGH_THRESHOLD,
    HUMIDITY_LOW_THRESHOLD, HUMIDITY_HIGH_THRESHOLD,
    LUX_DARK_THRESHOLD, LUX_DIM_THRESHOLD, LUX_BRIGHT_THRESHOLD
)
from data.database.setup_db import create_database
from data.database.db_manager import DatabaseManager


# ── 로그 설정 ──────────────────────────────────────
os.makedirs(LOG_DIR, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler()
    ]
)
log = logging.getLogger("Simulator")


# ── 가상 센서 데이터 생성기 ────────────────────────
class VirtualSensor:
    """
    실제 건물 환경을 모방한 가상 센서
    - 시간대별 온도/조도 변화 반영
    - 자연스러운 노이즈 추가
    - 가끔 이상값 발생 (실제 센서 특성 반영)
    """

    def __init__(self):
        self.call_count = 0

    def read_all(self) -> dict:
        self.call_count += 1
        now  = datetime.now()
        hour = now.hour + now.minute / 60.0  # 소수점 시각

        # ── 온도 (시간대별 변화) ───────────────────
        # 새벽 4시 최저(18℃), 오후 2시 최고(27℃) 사인 곡선
        base_temp = 22.5 + 4.5 * math.sin((hour - 4) * math.pi / 12)
        noise_temp = random.gauss(0, 0.3)   # 표준편차 0.3 노이즈
        temperature = round(base_temp + noise_temp, 2)

        # ── 습도 (온도 반비례 경향) ────────────────
        base_humidity = 60 - (temperature - 22) * 1.5
        noise_hum = random.gauss(0, 2)
        humidity = round(max(20, min(90, base_humidity + noise_hum)), 2)

        # ── 조도 (업무시간 밝음, 야간 어두움) ──────
        if 8 <= hour <= 18:
            # 업무 시간: 300~700 lux
            base_lux = 500 + 200 * math.sin((hour - 8) * math.pi / 10)
        elif 6 <= hour < 8 or 18 < hour <= 20:
            # 출퇴근 시간: 100~300 lux
            base_lux = 200
        else:
            # 야간: 5~50 lux
            base_lux = 20

        noise_lux = random.gauss(0, 20)
        lux = round(max(1, base_lux + noise_lux), 1)

        # ── 상태 분류 ──────────────────────────────
        def classify_temp(t):
            if   t < TEMP_LOW_THRESHOLD:  return "LOW"
            elif t > TEMP_HIGH_THRESHOLD: return "HIGH"
            return "NORMAL"

        def classify_hum(h):
            if   h < HUMIDITY_LOW_THRESHOLD:  return "DRY"
            elif h > HUMIDITY_HIGH_THRESHOLD: return "HUMID"
            return "NORMAL"

        def classify_lux(l):
            if   l < LUX_DARK_THRESHOLD:   return "DARK"
            elif l < LUX_DIM_THRESHOLD:    return "DIM"
            elif l < LUX_BRIGHT_THRESHOLD: return "NORMAL"
            return "VERY_BRIGHT"

        return {
            "timestamp":    now.strftime("%Y-%m-%d %H:%M:%S"),
            "temperature":  temperature,
            "humidity":     humidity,
            "lux":          lux,
            "temp_status":  classify_temp(temperature),
            "hum_status":   classify_hum(humidity),
            "light_status": classify_lux(lux),
            "all_success":  True
        }


# ── 수집 카운터 ────────────────────────────────────
_count_success = 0
_count_fail    = 0
virtual_sensor = None
db             = None


def collect_once():
    global _count_success, _count_fail

    data = virtual_sensor.read_all()
    data["location_id"] = LOCATION_ID

    log.info(
        f"[시뮬] "
        f"온도: {data['temperature']}℃ ({data['temp_status']}) | "
        f"습도: {data['humidity']}% ({data['hum_status']}) | "
        f"조도: {data['lux']} lux ({data['light_status']})"
    )

    saved = db.save_sensor_data(data)
    if saved:
        _count_success += 1
        total = db.get_total_count()
        log.info(f"[저장] ✅ 완료 (누적: {total:,}건)")
    else:
        _count_fail += 1
        log.warning("[저장] ❌ 실패")


def main():
    global virtual_sensor, db

    print("=" * 60)
    print("  🖥️  스마트 빌딩 AIoT - PC 시뮬레이터")
    print("=" * 60)
    print("  실제 라즈베리파이 없이 DB 저장 파이프라인 테스트")
    print(f"  수집 주기: {COLLECT_INTERVAL_SEC}초")
    print(f"  DB 경로  : {DB_PATH}")
    print("  종료     : Ctrl+C")
    print("=" * 60)
    print()

    # DB 초기화 (없으면 생성)
    if not os.path.exists(DB_PATH):
        print("DB가 없어서 자동 생성합니다...")
        create_database()

    db             = DatabaseManager(DB_PATH)
    virtual_sensor = VirtualSensor()

    # 즉시 1회 실행
    collect_once()

    # 이후 주기적 실행
    schedule.every(COLLECT_INTERVAL_SEC).seconds.do(collect_once)

    try:
        while True:
            schedule.run_pending()
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n\n시뮬레이터 종료")
        print(f"최종 결과: 성공 {_count_success}건 / 실패 {_count_fail}건")
        print(f"\n데이터 확인: python data/checker.py")


if __name__ == "__main__":
    main()
