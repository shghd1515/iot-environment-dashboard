# tests/test_bh1750.py
# ================================================
# BH1750 조도 센서 단독 테스트
# 실행: python3 tests/test_bh1750.py
# ================================================

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def lux_description(lux: float) -> str:
    """조도값을 사람이 읽기 쉬운 설명으로 변환"""
    if   lux <  50:   return "🌑 매우 어두움 (야간/암실)"
    elif lux <  100:  return "🌒 어두움 (복도/계단)"
    elif lux <  300:  return "🌓 약간 어두운 실내"
    elif lux <  500:  return "🌕 적절한 사무 조명"
    elif lux <  1000: return "☀️ 밝은 조명"
    elif lux <  5000: return "🔆 매우 밝음 (직사광선 근처)"
    else:             return "💥 직사광선"


def test_bh1750():
    print("=" * 55)
    print("  BH1750 조도 센서 테스트")
    print("=" * 55)
    print("  연결 확인:")
    print("    VCC  → Pin1  (3.3V)")
    print("    GND  → Pin9  (GND)")
    print("    SDA  → Pin3  (GPIO2/SDA)")
    print("    SCL  → Pin5  (GPIO3/SCL)")
    print("    ADDR → GND   (I2C주소 0x23 고정)")
    print("=" * 55)
    print()
    print("  💡 TIP: 손으로 센서를 가리거나 빛을 비추면서")
    print("         값이 변하는지 확인하세요!")
    print()

    try:
        from hardware.sensors.bh1750 import BH1750Sensor
        sensor = BH1750Sensor()
        print("✅ 센서 초기화 성공\n")

        success_count = 0
        readings      = []

        for i in range(1, 6):
            result = sensor.read()

            if result["success"]:
                success_count += 1
                lux = result["lux"]
                readings.append(lux)
                print(f"[{i}/5] 조도: {lux:>8.1f} lux  →  {lux_description(lux)}")
            else:
                print(f"[{i}/5] ❌ 읽기 실패")

            time.sleep(1)

        sensor.close()

        print()
        print("-" * 55)
        if readings:
            print(f"  최솟값: {min(readings)} lux")
            print(f"  최댓값: {max(readings)} lux")
            print(f"  평  균: {sum(readings)/len(readings):.1f} lux")
        print(f"  결  과: 성공 {success_count}/5  실패 {5-success_count}/5")
        if success_count >= 3:
            print("  판  정: ✅ 센서 정상 작동")
        else:
            print("  판  정: ❌ 센서 확인 필요")
            print("    → 'sudo i2cdetect -y 1' 로 0x23 감지 여부 확인")
            print("    → raspi-config에서 I2C 활성화 확인")
        print("=" * 55)

    except ImportError as e:
        print(f"❌ 라이브러리 없음: {e}")
        print("→ pip install smbus2 실행")
    except Exception as e:
        print(f"❌ 오류: {e}")
        print("→ SDA/SCL 배선 및 I2C 활성화를 확인하세요")


if __name__ == "__main__":
    test_bh1750()
