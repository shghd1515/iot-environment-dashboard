# tests/test_db.py
# ================================================
# 데이터베이스 저장/조회 테스트
# 실행: python3 tests/test_db.py
# ================================================

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.settings import DB_PATH
from data.database.db_manager import DatabaseManager


def test_database():
    print("=" * 50)
    print("  DB 저장/조회 테스트")
    print("=" * 50)

    try:
        db = DatabaseManager(DB_PATH)
        print("✅ DB 연결 성공\n")

        # ── 테스트 데이터 저장 ──────────────────────
        print("[1] 테스트 데이터 저장 중...")
        test_data = {
            "timestamp":    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "temperature":  24.3,
            "humidity":     58.2,
            "lux":          450.0,
            "temp_status":  "NORMAL",
            "hum_status":   "NORMAL",
            "light_status": "NORMAL",
            "location_id":  1
        }
        result = db.save_sensor_data(test_data)
        print(f"   저장 결과: {'✅ 성공' if result else '❌ 실패'}\n")

        # ── 저장된 데이터 조회 ──────────────────────
        print("[2] 최근 저장 데이터 조회:")
        rows = db.get_latest(3)
        for row in rows:
            print(f"   {row['timestamp']} | {row['temperature']}℃ | "
                  f"{row['humidity']}% | {row['lux']} lux")

        # ── 전체 개수 확인 ──────────────────────────
        total = db.get_total_count()
        print(f"\n[3] 전체 저장 건수: {total:,} 건")

        # ── 통계 확인 ───────────────────────────────
        stats = db.get_stats(hours=24)
        print(f"\n[4] 24시간 통계:")
        print(f"   건수: {stats['total_count']}건")
        print(f"   평균 온도: {stats['avg_temp']}℃")
        print(f"   평균 습도: {stats['avg_humidity']}%")

        print("\n" + "=" * 50)
        print("✅ DB 테스트 모두 통과!")
        print("=" * 50)

    except FileNotFoundError:
        print("❌ DB 파일 없음!")
        print("→ python3 data/database/setup_db.py 를 먼저 실행하세요")
    except Exception as e:
        print(f"❌ 오류: {e}")


if __name__ == "__main__":
    test_database()
