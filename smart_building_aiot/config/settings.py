# config/settings.py
# ================================================
# 스마트 빌딩 AIoT - 전체 설정 파일
# 여기서 핀 번호, 수집 주기, DB 경로 등을 변경하세요
# ================================================

import os

# ── 프로젝트 루트 경로 ─────────────────────────────
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ── 데이터베이스 설정 ──────────────────────────────
DB_PATH = os.path.join(BASE_DIR, "smart_building.db")

# ── 센서 GPIO 설정 ─────────────────────────────────
DHT22_PIN = 4           # GPIO 핀 번호 (BCM 기준) → Pin7 물리핀
BH1750_I2C_BUS = 1      # I2C 버스 번호 (라즈베리파이 = 1)
BH1750_ADDRESS = 0x23   # I2C 주소 (ADDR→GND: 0x23 / ADDR→VCC: 0x5C)

# ── 수집 설정 ──────────────────────────────────────
COLLECT_INTERVAL_SEC = 30   # 데이터 수집 주기 (초)
                             # 30 = 30초마다 / 60 = 1분마다
LOCATION_ID = 1              # 센서 위치 ID (방 번호 등)
LOCATION_NAME = "1층 사무실"  # 위치 이름

# ── 센서 유효 범위 (이 범위 벗어나면 오류로 처리) ────
TEMP_MIN = -10.0    # 최저 온도 (℃)
TEMP_MAX =  60.0    # 최고 온도 (℃)
HUMIDITY_MIN = 0.0  # 최저 습도 (%)
HUMIDITY_MAX = 100.0
LUX_MIN = 0.0       # 최저 조도 (lux)
LUX_MAX = 65535.0   # 최고 조도 (lux)

# ── 환경 상태 분류 기준 ────────────────────────────
# 온도
TEMP_LOW_THRESHOLD    = 18.0   # 18℃ 미만 → LOW (추움)
TEMP_HIGH_THRESHOLD   = 28.0   # 28℃ 초과 → HIGH (더움)
# NORMAL: 18~28℃

# 습도
HUMIDITY_LOW_THRESHOLD  = 30.0  # 30% 미만 → DRY
HUMIDITY_HIGH_THRESHOLD = 70.0  # 70% 초과 → HUMID
# NORMAL: 30~70%

# 조도
LUX_DARK_THRESHOLD   = 100.0   # 100 lux 미만 → DARK
LUX_DIM_THRESHOLD    = 400.0   # 400 lux 미만 → DIM
LUX_BRIGHT_THRESHOLD = 1000.0  # 1000 lux 초과 → VERY_BRIGHT
# NORMAL: 400~1000 lux

# ── 로그 설정 ──────────────────────────────────────
LOG_DIR  = os.path.join(BASE_DIR, "logs")
LOG_FILE = os.path.join(LOG_DIR, "collector.log")
LOG_MAX_BYTES   = 5 * 1024 * 1024  # 5MB
LOG_BACKUP_COUNT = 3                # 최대 3개 백업

# ── MySQL 접속 설정 ─────────────────────────
MYSQL_HOST     = '192.168.101.11'   # ← STEP 4에서 확인한 PC의 IP로 변경!
MYSQL_PORT     = 3306
MYSQL_USER     = 'smart_user'
MYSQL_PASSWORD = '00000'  # ← STEP 2에서 설정한 비밀번호
MYSQL_DATABASE = 'smart_building'
