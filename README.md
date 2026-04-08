# 🏠 IoT 스마트홈 환경 모니터링 대시보드

> 라즈베리파이 5 + 환경 센서 → Supabase → FastAPI + ML + AI → 실시간 웹 대시보드

[![Live Demo](https://img.shields.io/badge/Live%20Demo-Render-46E3B7?style=for-the-badge)](https://iot-environment-dashboard.onrender.com)
[![Python](https://img.shields.io/badge/Python-3.11-3776AB?style=for-the-badge&logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi)](https://fastapi.tiangolo.com)

---

## 📌 프로젝트 개요

라즈베리파이 5에 DHT22(온습도)와 PMS5003(미세먼지) 센서를 연결하여 실내 환경 데이터를 수집하고, Supabase PostgreSQL에 저장합니다. FastAPI 백엔드에서 머신러닝 모델과 Gemini AI를 통해 데이터를 분석하고, 웹 대시보드에서 실시간으로 시각화합니다.

---

## 🏗️ 시스템 아키텍처

```
[라즈베리파이 5]
  ├── DHT22 센서 (온도·습도)
  └── PMS5003 센서 (PM1·PM2.5·PM10)
         │
         ▼ psycopg2 (직접 저장, KST)
[Supabase PostgreSQL]
  └── sensor_combined 테이블
         │
         ▼ FastAPI (Render 배포)
[백엔드 서버]
  ├── ML 예측 (XGBoost / LightGBM / GradientBoosting)
  ├── Autoencoder 이상치 감지
  ├── Gemini 2.5 Flash AI 챗봇
  ├── 에어코리아 실시간/예보 API
  ├── 기상청 날씨 예보 API
  └── 생활기상지수 API
         │
         ▼ REST API
[웹 대시보드]
  ├── 실시간 센서 데이터 시각화
  ├── AI 권장값 및 건강 위험도
  ├── 시계열 차트 (24h·7d·30d)
  └── 외부 날씨·미세먼지 정보
```

---

## 🛠️ 기술 스택

| 구분 | 기술 |
|------|------|
| **하드웨어** | Raspberry Pi 5, DHT22, PMS5003 |
| **데이터베이스** | Supabase PostgreSQL |
| **백엔드** | FastAPI, Python 3.11 |
| **머신러닝** | XGBoost, LightGBM, RandomForest, GradientBoosting, scikit-learn |
| **AI** | Google Gemini 2.5 Flash |
| **프론트엔드** | Vanilla JS, Chart.js, HTML/CSS |
| **배포** | Render (백엔드), GitHub Pages (프론트엔드) |
| **알림** | Telegram Bot API |
| **외부 API** | 에어코리아, 기상청, 생활기상지수 |

---

## 📁 프로젝트 구조

```
backend/
├── 01_preprocess.py        # 데이터 전처리 및 피처 엔지니어링 (39개 피처)
├── 03_train_model.py       # ML 모델 학습 (4개 모델 비교 후 최적 선택)
├── 04_autoencoder.py       # Autoencoder 이상치 감지 모델 학습
├── 04_fastapi_app.py       # FastAPI 메인 서버
├── 05_auto_scheduler.py    # 자동화 스케줄러 (알림·이벤트 분류·주간리포트)
├── chatbot.py              # Gemini AI 챗봇
├── requirements.txt
├── Procfile
└── models/
    ├── model_temp.pkl          # 온도 예측 모델 (GradientBoosting)
    ├── model_humi.pkl          # 습도 예측 모델 (GradientBoosting)
    ├── model_pm25.pkl          # PM2.5 예측 모델 (LightGBM)
    ├── autoencoder.pkl         # Autoencoder 이상치 감지
    ├── autoencoder_scaler.pkl
    ├── autoencoder_meta.pkl
    ├── scaler.pkl
    ├── feature_names.pkl
    ├── feature_names_pm25.pkl
    ├── hourly_pattern.json
    └── metadata.json

frontend/
└── index.html              # 단일 파일 대시보드

.github/
└── workflows/
    └── retrain.yml         # 매주 일요일 03시 ML 자동 재학습
```

---

## 🤖 머신러닝 모델

### 예측 모델 성능 (CV MAE 기준)

| 항목 | 최적 모델 | CV MAE | 이전 대비 향상 |
|------|-----------|--------|----------------|
| 온도 | GradientBoosting | 0.0717 | **68% 향상** |
| 습도 | GradientBoosting | 0.1163 | **79% 향상** |
| PM2.5 | LightGBM | 9.9132 | - |

### 피처 엔지니어링 (12개 → 39개)

- 시간 주기성: `month_sin/cos`, `minute_sin/cos`, `time_group`
- 이동 통계: `ma120`, `std10`
- 변화율: `diff5`, `diff10`, `accel`
- 교차 피처: `temp_humi` 곱

### 추천값 계산 방식

```
추천값 = ML 예측 × 0.7 + 시간대별 패턴 × 0.3
```

### Autoencoder 이상치 감지

- 구조: MLPRegressor (8→4→8, scikit-learn)
- 임계값: 0.101309 (상위 5% 기준)
- 이상 점수 150 초과 시 텔레그램 알림 자동 발송

---

## 🌡️ 건강 위험도 점수

PM2.5·온도·습도 값을 가중 합산하여 0~100점 건강 위험도를 실시간 계산합니다.

| 항목 | 가중치 |
|------|--------|
| PM2.5 | 50% |
| 온도 | 25% |
| 습도 | 25% |

---

## 🔔 알림 시스템

텔레그램 봇을 통해 아래 조건 발생 시 자동 알림을 발송합니다. 수면 모드(23시~07시)에는 무음 처리됩니다.

| 항목 | 조건 |
|------|------|
| PM2.5 | ≥ 35 µg/m³ |
| 온도 | ≥ 28°C 또는 ≤ 15°C |
| 습도 | ≥ 70% 또는 ≤ 30% |
| 이상치 | Autoencoder 점수 > 150 |
| 주간 리포트 | 매주 일요일 20시 |

---

## 🎯 이벤트 자동 분류

실내 환경 변화 패턴을 분석하여 생활 이벤트를 자동으로 분류합니다.

| 이벤트 | 조건 |
|--------|------|
| 요리 감지 | PM2.5 급등(≥15) + 온도 상승(≥0.5) |
| 청소 감지 | PM2.5 급등(≥15) + 온도 변화 없음 |
| 환기 감지 | PM2.5 급감(≤-10) + 온도 하강(≤-0.5) |
| 외출 감지 | 온도(≤-1.0) + 습도(≤-2.0) 동시 하강 |
| 귀가 감지 | 온도(≥1.0) + 습도(≥2.0) 동시 상승 |

---

## 🗺️ API 엔드포인트

| 메서드 | 경로 | 설명 |
|--------|------|------|
| GET | `/status` | 현재 센서값 + AI 권장값 + 건강점수 |
| GET | `/forecast?hours=3` | 향후 환경 예측 |
| GET | `/anomaly` | Autoencoder 이상치 점수 |
| GET | `/outdoor-air` | 에어코리아 실시간 미세먼지 |
| GET | `/air-forecast` | 에어코리아 미세먼지 예보 |
| GET | `/weather-forecast` | 기상청 날씨 예보 (12시간) |
| GET | `/living-index` | 생활기상지수 (자외선·대기정체) |
| GET | `/pattern` | 시간대별 환경 패턴 |
| GET | `/correlation` | 온습도 상관관계 |
| GET | `/history?range=24h\|7d\|30d` | 기간별 센서 데이터 |
| GET | `/alerts` | 알림 히스토리 |
| POST | `/chat` | Gemini AI 챗봇 |

---

## 📊 대시보드 기능

- **실시간 모니터링**: 온도·습도·PM2.5·PM10 현재값
- **건강 위험도**: 원형 게이지 점수 (0~100점)
- **환경 예측**: 향후 3시간 예측값
- **실내외 비교**: 실내 vs 에어코리아 실외 미세먼지 + 환기 추천
- **AI 권장값**: ML 모델 기반 적정 온습도·PM2.5 권장
- **시계열 차트**: 24시간·7일·30일 선택 가능
- **시간대별 패턴**: 요일·시간대별 평균 환경 분석
- **온습도 상관관계**: 산점도 분석
- **미세먼지 예보**: 에어코리아 오늘 예보
- **날씨 예보**: 기상청 향후 12시간 예보
- **생활기상지수**: 자외선 지수 + 대기정체지수
- **AI 챗봇**: Gemini 2.5 Flash 기반 환경 질의응답
- **다크모드**: 시스템 설정 연동
- **모바일 반응형**: 하단 고정 챗봇 포함
- **드래그앤드롭**: 위젯 순서 사용자 정의

---

## ⚙️ 설치 및 실행

### 1. 환경변수 설정

Render 대시보드 → Environment에 아래 환경변수를 설정합니다.

```
SUPABASE_DB_URL=postgresql://...
GEMINI_API_KEY=...
TELEGRAM_TOKEN=...
TELEGRAM_CHAT_ID=...
AIR_API_KEY=...
```

### 2. 의존성 설치

```bash
pip install -r requirements.txt
```

### 3. ML 모델 학습

```bash
python 01_preprocess.py
python 03_train_model.py
python 04_autoencoder.py
```

### 4. 서버 실행

```bash
uvicorn 04_fastapi_app:app --host 0.0.0.0 --port 8000
```

---

## 🔄 자동화

- **ML 재학습**: GitHub Actions로 매주 일요일 03시 자동 실행 (`.github/workflows/retrain.yml`)
- **서버 슬립 방지**: UptimeRobot으로 5분마다 핑
- **스케줄러**: `05_auto_scheduler.py` - 이벤트 분류, 이상치 감지, 주간 리포트 자동 실행

---

## 🗄️ 데이터베이스 스키마

### sensor_combined
| 컬럼 | 타입 | 설명 |
|------|------|------|
| id | SERIAL PK | 고유 ID |
| temperature | FLOAT | 온도 (°C) |
| humidity | FLOAT | 습도 (%) |
| pm1 | FLOAT | PM1.0 (µg/m³) |
| pm25 | FLOAT | PM2.5 (µg/m³) |
| pm10 | FLOAT | PM10 (µg/m³) |
| event | TEXT | 자동 분류 이벤트 |
| recorded_at | TIMESTAMPTZ | 측정 시각 (KST) |

### alert_logs
알림 발송 이력 (alert_type, message, value, threshold, created_at)

### auth_logs
로그인·로그아웃·방문 기록 (email, user_id, action, created_at)

---

## 📝 향후 계획

- [ ] LSTM 시계열 예측 모델 (데이터 30,000개 이상 확보 후)
- [ ] 꽃가루 API 연동 (서비스 개방 시)
- [ ] PWA 모바일 앱 변환

---

## 👤 개발자

노홍욱 | [GitHub](https://github.com/shghd1515/iot-environment-dashboard)
