# hardware/sensors/dht22.py
# ================================================
# DHT22 온습도 센서 드라이버
# 연결: GPIO4 핀 (BCM 기준), 10kΩ 풀업저항 필요
# ================================================

import time
import logging
from config.settings import (
    DHT22_PIN, TEMP_MIN, TEMP_MAX,
    HUMIDITY_MIN, HUMIDITY_MAX
)

log = logging.getLogger(__name__)


class DHT22Sensor:
    """
    DHT22 온습도 센서 클래스
    - 최소 측정 간격: 2초 (센서 스펙)
    - 측정 실패 시 최대 3회 재시도
    """

    MAX_RETRIES = 3        # 최대 재시도 횟수
    RETRY_DELAY = 2.0      # 재시도 대기 시간 (초)

    def __init__(self):
        self._sensor = None
        self._initialize()

    def _initialize(self):
        """센서 초기화 - adafruit 라이브러리 로드"""
        try:
            import board
            import adafruit_dht

            # board.D4 = GPIO4 핀
            pin = getattr(board, f"D{DHT22_PIN}")
            self._sensor = adafruit_dht.DHT22(pin, use_pulseio=False)
            log.info(f"DHT22 초기화 완료 (GPIO{DHT22_PIN})")

        except ImportError:
            log.error("adafruit_dht 라이브러리가 없습니다. requirements.txt 확인!")
            raise
        except Exception as e:
            log.error(f"DHT22 초기화 실패: {e}")
            raise

    def read(self) -> dict:
        """
        온도/습도 읽기
        반환값: {"temperature": 24.3, "humidity": 58.2, "success": True}
        실패 시: {"temperature": None, "humidity": None, "success": False}
        """
        for attempt in range(1, self.MAX_RETRIES + 1):
            try:
                temperature = self._sensor.temperature
                humidity    = self._sensor.humidity

                # None 체크
                if temperature is None or humidity is None:
                    raise ValueError("센서에서 None 값 반환")

                # 유효 범위 체크
                if not (TEMP_MIN <= temperature <= TEMP_MAX):
                    raise ValueError(f"온도 범위 초과: {temperature}℃")
                if not (HUMIDITY_MIN <= humidity <= HUMIDITY_MAX):
                    raise ValueError(f"습도 범위 초과: {humidity}%")

                # 소수점 2자리로 반올림
                return {
                    "temperature": round(temperature, 2),
                    "humidity":    round(humidity, 2),
                    "success":     True
                }

            except RuntimeError as e:
                # RuntimeError는 DHT22에서 자주 발생하는 타이밍 오류 → 정상
                log.warning(f"DHT22 읽기 실패 ({attempt}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)

            except ValueError as e:
                log.warning(f"DHT22 유효성 오류 ({attempt}/{self.MAX_RETRIES}): {e}")
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_DELAY)

            except Exception as e:
                log.error(f"DHT22 예상치 못한 오류: {e}")
                break

        # 모든 재시도 실패
        log.error(f"DHT22 {self.MAX_RETRIES}회 시도 모두 실패")
        return {"temperature": None, "humidity": None, "success": False}

    def close(self):
        """센서 종료"""
        if self._sensor:
            try:
                self._sensor.exit()
                log.info("DHT22 종료")
            except Exception:
                pass
