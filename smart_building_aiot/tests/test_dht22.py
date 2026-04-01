# tests/test_dht22.py
# ================================================
# DHT22 센서 단독 테스트
# 실행: python3 tests/test_dht22.py
# ================================================

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_dht22():
    print("=" * 50)
    print("  DHT22 온습도 센서 테스트")
    print("=" * 50)
    print("  연결 확인:")
    print("    VCC  → Pin1  (3.3V)")
    print("    DATA → Pin7  (GPIO4) + 10kΩ 풀업저항")
    print("    GND  → Pin6  (GND)")
    print("=" * 50)
    print()

    try:
        from hardware.sensors.dht22 import DHT22Sensor
        sensor = DHT22Sensor()
        print("✅ 센서 초기화 성공\n")

        success_count = 0
        fail_count    = 0

        for i in range(1, 6):
            print(f"[{i}/5번째 측정]")
            result = sensor.read()

            if result["success"]:
                success_count += 1
                print(f"  온도: {result['temperature']} ℃")
                print(f"  습도: {result['humidity']} %")
                print(f"  상태: ✅ 정상\n")
            else:
                fail_count += 1
                print(f"  상태: ❌ 읽기 실패\n")

            time.sleep(2)  # DHT22 최소 2초 간격 필수

        sensor.close()

        print("-" * 50)
        print(f"  결과: 성공 {success_count}/5  실패 {fail_count}/5")
        if success_count >= 3:
            print("  판정: ✅ 센서 정상 작동")
        else:
            print("  판정: ❌ 센서 확인 필요 (배선 재확인)")
        print("=" * 50)

    except ImportError as e:
        print(f"❌ 라이브러리 없음: {e}")
        print("→ pip install adafruit-circuitpython-dht 실행")
    except Exception as e:
        print(f"❌ 오류 발생: {e}")
        print("→ GPIO4 핀 배선을 확인하세요")


if __name__ == "__main__":
    test_dht22()
