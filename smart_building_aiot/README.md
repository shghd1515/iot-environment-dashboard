# 🏢 Smart Building AIoT - 라즈베리파이 데이터 수집 시스템

## 📋 프로젝트 개요
라즈베리파이에 DHT22(온습도)와 BH1750(조도) 센서를 연결하여
30초마다 자동으로 데이터를 수집하고 SQLite DB에 저장하는 시스템

---

## 🗂️ 폴더 구조
```
smart_building_aiot/
├── hardware/
│   └── sensors/
│       ├── dht22.py          # DHT22 온습도 센서 드라이버
│       ├── bh1750.py         # BH1750 조도 센서 드라이버
│       └── sensor_manager.py # 통합 센서 관리자
├── data/
│   ├── database/
│   │   ├── setup_db.py       # DB 초기 생성
│   │   └── db_manager.py     # DB CRUD 관리
│   ├── collector.py          # 메인 데이터 수집기
│   └── checker.py            # 수집된 데이터 확인
├── config/
│   └── settings.py           # 전체 설정값
├── tests/
│   ├── test_dht22.py         # DHT22 단독 테스트
│   ├── test_bh1750.py        # BH1750 단독 테스트
│   └── test_db.py            # DB 저장 테스트
├── logs/                     # 로그 파일 저장 폴더
├── simulator.py              # 라즈베리파이 없을 때 PC 테스트용
├── main.py                   # 최종 실행 파일
└── requirements.txt
```

---

## 🔌 하드웨어 연결

### 필요 부품
- 라즈베리파이 4 (또는 3B+)
- DHT22 센서 1개
- BH1750 센서 1개
- 10kΩ 저항 1개 (DHT22 풀업용)
- 브레드보드 + 점퍼선

### 회로 연결
```
[DHT22]
  VCC  → 라즈베리파이 Pin1  (3.3V)
  DATA → 라즈베리파이 Pin7  (GPIO4)  + 10kΩ 저항(VCC↔DATA 사이)
  GND  → 라즈베리파이 Pin6  (GND)

[BH1750]
  VCC  → 라즈베리파이 Pin1  (3.3V)
  GND  → 라즈베리파이 Pin9  (GND)
  SDA  → 라즈베리파이 Pin3  (GPIO2/SDA)
  SCL  → 라즈베리파이 Pin5  (GPIO3/SCL)
  ADDR → GND (I2C 주소 0x23 고정)
```

---

## 🚀 실행 순서 (라즈베리파이)

### 1단계: 라즈베리파이 초기 설정
```bash
# I2C 활성화
sudo raspi-config
# → Interface Options → I2C → Enable → Finish

# 시스템 업데이트
sudo apt update && sudo apt upgrade -y
sudo apt install libgpiod2 -y

# I2C 센서 감지 확인 (0x23이 보이면 성공)
sudo i2cdetect -y 1
```

### 2단계: 프로젝트 설치
```bash
# 프로젝트 폴더를 라즈베리파이로 복사 후
cd ~/smart_building_aiot

# 가상환경 생성
python3 -m venv venv
source venv/bin/activate

# 라이브러리 설치
pip install -r requirements.txt
```

### 3단계: DB 초기화
```bash
python3 data/database/setup_db.py
```

### 4단계: 센서 테스트
```bash
python3 tests/test_dht22.py    # DHT22 작동 확인
python3 tests/test_bh1750.py   # BH1750 작동 확인
```

### 5단계: 데이터 수집 시작
```bash
python3 main.py
```

### 6단계: 수집 데이터 확인
```bash
python3 data/checker.py
```

---

## 💻 PC에서 테스트 (라즈베리파이 없을 때)
```bash
# 가상환경 생성 (Windows)
python -m venv venv
venv\Scripts\activate

# 시뮬레이터 전용 라이브러리만 설치
pip install schedule pandas

# 시뮬레이터 실행 (가짜 센서 데이터로 DB 저장 테스트)
python simulator.py
```

---

## 🔁 부팅 시 자동 시작 설정 (라즈베리파이)
```bash
sudo nano /etc/systemd/system/smart-building.service
# → 파일 내용은 README 하단 참고

sudo systemctl enable smart-building
sudo systemctl start smart-building
sudo systemctl status smart-building
```

### systemd 서비스 파일 내용
```ini
[Unit]
Description=Smart Building Data Collector
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/smart_building_aiot
ExecStart=/home/pi/smart_building_aiot/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

---

## 📊 DB 파일 위치
- 경로: `smart_building_aiot/smart_building.db`
- VS Code에서 확인: SQLite Viewer 확장 설치 후 .db 파일 클릭

## 🛠️ VS Code 추천 확장
- Python (Microsoft)
- Pylance
- SQLite Viewer
- GitLens
