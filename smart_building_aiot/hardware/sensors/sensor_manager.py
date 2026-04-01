# hardware/sensors/sensor_manager.py
# ================================================
# 통합 센서 관리자
# DHT22 + BH1750 동시 읽기 및 데이터 통합
# ================================================

import logging
from datetime import datetime
from hardware.sensors.dht22 import DHT22Sensor
from hardware.sensors.bh1750 import BH1750Sensor
from config.settings import (
    TEMP_LOW_THRESHOLD, TEMP_HIGH_THRESHOLD,
    HUMIDITY_LOW_THRESHOLD, HUMIDITY_HIGH_THRESHOLD,
    LUX_DARK_THRESHOLD, LUX_DIM_THRESHOLD, LUX_BRIGHT_THRESHOLD
)

log = logging.getLogger(__name__)


class SensorManager:
    """
    DHT22 + BH1750 통합 관리 클래스
    - 두 센서를 동시에 초기화/읽기/종료
    - 읽은 값에 상태 분류 자동 추가
    """

    def __init__(self):
        log.info("센서 매니저 초기화 중...")
        self.dht22  = DHT22Sensor()
        self.bh1750 = BH1750Sensor()
        log.info("모든 센서 초기화 완료")

    def _classify_temperature(self, temp: float) -> str:
        """온도 상태 분류"""
        if   temp < TEMP_LOW_THRESHOLD:  return "LOW"     # 춥다
        elif temp > TEMP_HIGH_THRESHOLD: return "HIGH"    # 덥다
        else:                            return "NORMAL"  # 적절

    def _classify_humidity(self, hum: float) -> str:
        """습도 상태 분류"""
        if   hum < HUMIDITY_LOW_THRESHOLD:  return "DRY"    # 건조
        elif hum > HUMIDITY_HIGH_THRESHOLD: return "HUMID"  # 습함
        else:                               return "NORMAL"

    def _classify_light(self, lux: float) -> str:
        """조도 상태 분류"""
        if   lux < LUX_DARK_THRESHOLD:   return "DARK"        # 매우 어두움
        elif lux < LUX_DIM_THRESHOLD:    return "DIM"         # 어두운 실내
        elif lux < LUX_BRIGHT_THRESHOLD: return "NORMAL"      # 적절한 조명
        else:                            return "VERY_BRIGHT"  # 매우 밝음

    def read_all(self) -> dict:
        """
        모든 센서 읽기 + 상태 분류
        반환값:
        {
            "timestamp":    "2024-01-15 14:30:00",
            "temperature":  24.3,
            "humidity":     58.2,
            "lux":          450.5,
            "temp_status":  "NORMAL",
            "hum_status":   "NORMAL",
            "light_status": "NORMAL",
            "all_success":  True
        }
        """
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # 센서 읽기
        dht_data  = self.dht22.read()
        lux_data  = self.bh1750.read()

        temp = dht_data["temperature"]
        hum  = dht_data["humidity"]
        lux  = lux_data["lux"]

        # 상태 분류 (None이면 "ERROR")
        temp_status  = self._classify_temperature(temp) if temp is not None else "ERROR"
        hum_status   = self._classify_humidity(hum)     if hum  is not None else "ERROR"
        light_status = self._classify_light(lux)        if lux  is not None else "ERROR"

        all_success = dht_data["success"] and lux_data["success"]

        result = {
            "timestamp":    now,
            "temperature":  temp,
            "humidity":     hum,
            "lux":          lux,
            "temp_status":  temp_status,
            "hum_status":   hum_status,
            "light_status": light_status,
            "all_success":  all_success
        }

        if all_success:
            log.debug(f"센서 읽기 성공: {temp}℃ / {hum}% / {lux}lux")
        else:
            log.warning(f"일부 센서 읽기 실패: temp={temp}, hum={hum}, lux={lux}")

        return result

    def close(self):
        """모든 센서 종료"""
        self.dht22.close()
        self.bh1750.close()
        log.info("모든 센서 종료")
