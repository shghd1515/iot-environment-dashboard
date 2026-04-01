# hardware/sensors/bh1750.py
# ================================================
# BH1750 조도 센서 드라이버 (I2C 통신)
# 연결: SDA(Pin3), SCL(Pin5), ADDR→GND(주소 0x23)
# ================================================

import time
import logging
from config.settings import BH1750_I2C_BUS, BH1750_ADDRESS, LUX_MIN, LUX_MAX

log = logging.getLogger(__name__)


class BH1750Sensor:
    """
    BH1750 조도 센서 클래스
    - 통신 방식: I2C
    - 측정 범위: 1 ~ 65535 lux
    - 해상도: 1 lux (HIGH_RES 모드)
    """

    # BH1750 측정 모드 명령어
    POWER_ON          = 0x01   # 전원 켜기
    RESET             = 0x07   # 리셋
    CONT_HIGH_RES     = 0x10   # 연속 측정, 1lux 해상도, 120ms
    CONT_HIGH_RES2    = 0x11   # 연속 측정, 0.5lux 해상도, 120ms
    CONT_LOW_RES      = 0x13   # 연속 측정, 4lux 해상도, 16ms
    ONE_HIGH_RES      = 0x20   # 1회 측정 후 슬립

    def __init__(self):
        self._bus = None
        self._initialize()

    def _initialize(self):
        """I2C 버스 초기화 및 센서 켜기"""
        try:
            import smbus2
            self._bus = smbus2.SMBus(BH1750_I2C_BUS)

            # 센서 전원 ON
            self._bus.write_byte(BH1750_ADDRESS, self.POWER_ON)
            time.sleep(0.01)

            # 연속 고해상도 측정 모드 설정
            self._bus.write_byte(BH1750_ADDRESS, self.CONT_HIGH_RES)
            time.sleep(0.18)  # 측정 완료 대기 (120ms + 여유)

            log.info(f"BH1750 초기화 완료 (I2C 주소: {hex(BH1750_ADDRESS)})")

        except ImportError:
            log.error("smbus2 라이브러리가 없습니다. requirements.txt 확인!")
            raise
        except OSError as e:
            log.error(f"BH1750 I2C 연결 실패: {e}")
            log.error("→ 'sudo raspi-config'에서 I2C가 활성화되었는지 확인하세요")
            log.error("→ 배선 연결(SDA/SCL)을 확인하세요")
            raise
        except Exception as e:
            log.error(f"BH1750 초기화 실패: {e}")
            raise

    def read(self) -> dict:
        """
        조도 읽기
        반환값: {"lux": 450.5, "success": True}
        실패 시: {"lux": None, "success": False}
        """
        try:
            # 2바이트 읽기
            data = self._bus.read_i2c_block_data(BH1750_ADDRESS, self.CONT_HIGH_RES, 2)

            # 상위바이트 << 8 | 하위바이트 → 감도 보정 (÷1.2)
            raw_value = (data[0] << 8) | data[1]
            lux = raw_value / 1.2

            # 유효 범위 체크
            if not (LUX_MIN <= lux <= LUX_MAX):
                raise ValueError(f"조도 범위 초과: {lux} lux")

            return {
                "lux":     round(lux, 1),
                "success": True
            }

        except OSError as e:
            log.error(f"BH1750 I2C 읽기 오류: {e}")
            return {"lux": None, "success": False}

        except ValueError as e:
            log.warning(f"BH1750 유효성 오류: {e}")
            return {"lux": None, "success": False}

        except Exception as e:
            log.error(f"BH1750 예상치 못한 오류: {e}")
            return {"lux": None, "success": False}

    def close(self):
        """I2C 버스 종료"""
        if self._bus:
            try:
                self._bus.close()
                log.info("BH1750 I2C 버스 종료")
            except Exception:
                pass
