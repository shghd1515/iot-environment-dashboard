"""
04_fastapi_app.py (최종 버전)
Gemini 챗봇 + 자동제어 + 환기 알람 통합

변경사항:
  - 06_chatbot.py 라우터 통합
  - frontend index.html 정적 파일 서빙 추가

실행:
    uvicorn 04_fastapi_app:app --host 0.0.0.0 --port 8000 --reload
"""

import os, json, math, joblib
import pandas as pd
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from apscheduler.schedulers.background import BackgroundScheduler

# 챗봇 라우터 임포트
from chatbot import router as chatbot_router

load_dotenv()

# ── DB 연결 ───────────────────────────────────────────────────────────────────
def get_engine():
    supabase_url = os.getenv("SUPABASE_DB_URL")
    if supabase_url:
        return create_engine(supabase_url, pool_pre_ping=True)
    url = (
        f"mysql+pymysql://{os.getenv('DB_USER','root01')}:{os.getenv('DB_PASSWORD','00000')}"
        f"@{os.getenv('DB_HOST','192.168.101.2')}:{os.getenv('DB_PORT','3307')}"
        f"/{os.getenv('DB_NAME','sensor_db')}?charset=utf8mb4"
    )
    return create_engine(url, pool_pre_ping=True)

engine    = get_engine()
scheduler = BackgroundScheduler()

# ── 모델 저장소 ───────────────────────────────────────────────────────────────
MODEL_DIR = "models"

class ModelStore:
    model_temp = model_humi = model_pm25 = None
    scaler = feature_names = hourly_pattern = None
    metadata = {}

store = ModelStore()

def load_models() -> bool:
    required = ["model_temp.pkl", "model_humi.pkl", "scaler.pkl", "feature_names.pkl"]
    for f in required:
        if not os.path.exists(os.path.join(MODEL_DIR, f)):
            print(f"[경고] 모델 없음: {f}")
            return False
    store.model_temp    = joblib.load(os.path.join(MODEL_DIR, "model_temp.pkl"))
    store.model_humi    = joblib.load(os.path.join(MODEL_DIR, "model_humi.pkl"))
    store.scaler        = joblib.load(os.path.join(MODEL_DIR, "scaler.pkl"))
    store.feature_names = joblib.load(os.path.join(MODEL_DIR, "feature_names.pkl"))
    pm25_path = os.path.join(MODEL_DIR, "model_pm25.pkl")
    if os.path.exists(pm25_path):
        store.model_pm25 = joblib.load(pm25_path)
    p = os.path.join(MODEL_DIR, "hourly_pattern.json")
    if os.path.exists(p):
        store.hourly_pattern = {
            (int(x["hour"]), int(x["is_weekend"])): x
            for x in json.load(open(p, encoding="utf-8"))
        }
    m = os.path.join(MODEL_DIR, "metadata.json")
    if os.path.exists(m):
        store.metadata = json.load(open(m, encoding="utf-8"))
    print(f"[모델] 로드 완료 ({store.metadata.get('trained_at','?')})")
    return True


# ── 환기 알람 ────────────────────────────────────────────────────────────────
def ventilation_alarm():
    now = datetime.now()
    print(f"\n{'='*50}")
    print(f"[알람] 오후 2시! 지금 창문을 열어 15분 환기하세요!")
    print(f"{'='*50}\n")
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE sensor_combined SET event = '환기시작' "
                "WHERE recorded_at = (SELECT MAX(recorded_at) FROM "
                "(SELECT recorded_at FROM sensor_combined) AS t)"
            ))
            conn.commit()
        print(f"[이벤트] 환기시작 기록: {now.strftime('%H:%M')}")
    except Exception as e:
        print(f"[이벤트 오류] {e}")

def ventilation_end():
    print(f"\n[알람] 15분 환기 완료! 창문을 닫으세요.")
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE sensor_combined SET event = '환기종료' "
                "WHERE recorded_at = (SELECT MAX(recorded_at) FROM "
                "(SELECT recorded_at FROM sensor_combined) AS t)"
            ))
            conn.commit()
        print(f"[이벤트] 환기종료 기록 완료")
    except Exception as e:
        print(f"[이벤트 오류] {e}")


# ── 앱 초기화 ─────────────────────────────────────────────────────────────────
@asynccontextmanager
async def lifespan(app: FastAPI):
    load_models()
    scheduler.add_job(ventilation_alarm, "cron", hour=14, minute=0,  id="vent_start")
    scheduler.add_job(ventilation_end,   "cron", hour=14, minute=15, id="vent_end")
    scheduler.start()
    print("[스케줄러] 오후 2시 환기 알람 등록 완료")
    yield
    scheduler.shutdown()

app = FastAPI(
    title="IoT 환경 자동제어 AI",
    description="DHT22 + PMS5003 + ML + Gemini 기반 스마트홈 API",
    version="3.0.0",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

# 챗봇 라우터 등록
app.include_router(chatbot_router)

# frontend 정적 파일 서빙
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")
if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")


# ── 유틸 ──────────────────────────────────────────────────────────────────────
def get_latest_sensor() -> dict:
    sql = """SELECT recorded_at, temperature, humidity, pm1, pm25, pm10, event
             FROM sensor_combined ORDER BY recorded_at DESC LIMIT 1"""
    try:
        with engine.connect() as conn:
            row = conn.execute(text(sql)).fetchone()
        if row:
            return {"recorded_at": str(row[0]), "temperature": row[1],
                    "humidity": row[2], "pm1": row[3],
                    "pm25": row[4], "pm10": row[5], "event": row[6]}
    except Exception as e:
        print(f"[DB 오류] {e}")
    return {}

def get_recommendation(hour, is_weekend, curr_temp, curr_humi, curr_pm25=0.0):
    def _pattern():
        if store.hourly_pattern:
            p = store.hourly_pattern.get((hour, is_weekend)) or \
                store.hourly_pattern.get((hour, 0))
            if p:
                return {"temperature": p.get("target_temp", 22.0),
                        "humidity": p.get("target_humi", 50.0),
                        "pm25": p.get("target_pm25", 20.0)}
        return {"temperature": 22.0, "humidity": 50.0, "pm25": 20.0}

    if store.model_temp is None:
        r = _pattern(); r["method"] = "pattern_lookup"; return r

    dow = 5 if is_weekend else 2
    feats = {
        "hour_sin": math.sin(2*math.pi*hour/24), "hour_cos": math.cos(2*math.pi*hour/24),
        "dow_sin":  math.sin(2*math.pi*dow/7),   "dow_cos":  math.cos(2*math.pi*dow/7),
        "is_weekend": float(is_weekend),
        "temp_ma60": curr_temp, "humi_ma60": curr_humi, "pm25_ma60": curr_pm25,
        "temp_diff": 0.0, "humi_diff": 0.0, "pm25_diff": 0.0, "has_event": 0.0,
    }
    row = pd.DataFrame([[feats.get(f, 0.0) for f in store.feature_names]],
                       columns=store.feature_names)
    X_s = store.scaler.transform(row)
    ml  = {
        "temperature": round(float(store.model_temp.predict(X_s)[0]), 2),
        "humidity":    round(float(store.model_humi.predict(X_s)[0]), 2),
        "pm25":        round(float(store.model_pm25.predict(X_s)[0]), 2)
                       if store.model_pm25 else curr_pm25,
    }
    pat    = _pattern()
    n      = store.metadata.get("n_samples", 0)
    wm, wp = (0.3, 0.7) if n < 5000 else (0.7, 0.3)
    return {
        "temperature": round(ml["temperature"]*wm + pat["temperature"]*wp, 2),
        "humidity":    round(ml["humidity"]   *wm + pat["humidity"]   *wp, 2),
        "pm25":        round(ml["pm25"]       *wm + pat["pm25"]       *wp, 2),
        "method":      f"blend(ml={wm}, pattern={wp})",
    }


# ── 스키마 ────────────────────────────────────────────────────────────────────
class PredictRequest(BaseModel):
    hour: int = 12; is_weekend: int = 0
    current_temp: float = 23.0; current_humi: float = 43.0; current_pm25: float = 25.0

class EventRequest(BaseModel):
    event_name: str


# ── 엔드포인트 ────────────────────────────────────────────────────────────────
@app.get("/", summary="대시보드 UI")
def dashboard():
    path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(path):
        return FileResponse(path)
    return {"message": "frontend/index.html 파일을 확인해주세요"}

@app.get("/status", summary="현재 센서값 + AI 권장값", tags=["ML 제어"])
def get_status():
    s = get_latest_sensor(); now = datetime.now(); w = int(now.weekday() >= 5)
    rec = get_recommendation(now.hour, w,
                             s.get("temperature", 23.0),
                             s.get("humidity", 43.0),
                             s.get("pm25") or 25.0)
    return {
        "current": s,
        "recommendation": {"hour": now.hour, "is_weekend": w, **rec},
        "diff": {
            "temp_diff": round(rec["temperature"] - (s.get("temperature") or 0), 2),
            "humi_diff": round(rec["humidity"]    - (s.get("humidity") or 0),    2),
            "pm25_diff": round(rec["pm25"]        - (s.get("pm25") or 0),        2),
        }
    }

@app.post("/predict", summary="조건 기반 ML 예측", tags=["ML 제어"])
def predict(req: PredictRequest):
    return {"input": req.model_dump(),
            "output": get_recommendation(req.hour, req.is_weekend,
                                         req.current_temp, req.current_humi,
                                         req.current_pm25)}

@app.get("/schedule", summary="오늘 24시간 스케줄", tags=["ML 제어"])
def get_schedule():
    now = datetime.now(); w = int(now.weekday() >= 5); s = get_latest_sensor()
    return {
        "date": now.strftime("%Y-%m-%d"), "is_weekend": w,
        "ventilation_time": "14:00",
        "schedule": [
            {**get_recommendation(h, w, s.get("temperature",23.0),
                                  s.get("humidity",43.0), s.get("pm25") or 25.0),
             "hour": h, "is_active": h == now.hour, "is_ventilation": h == 14}
            for h in range(24)
        ]
    }

@app.post("/event", summary="이벤트 수동 기록", tags=["이벤트"])
def record_event(req: EventRequest):
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE sensor_combined SET event = :e "
                "WHERE recorded_at = (SELECT MAX(recorded_at) FROM "
                "(SELECT recorded_at FROM sensor_combined) AS t)"
            ), {"e": req.event_name})
            conn.commit()
        return {"message": f"이벤트 기록: {req.event_name}",
                "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    except Exception as e:
        raise HTTPException(500, str(e))

@app.post("/retrain", summary="모델 재학습", tags=["모델"])
def retrain(background_tasks: BackgroundTasks):
    def _job():
        import subprocess, sys
        subprocess.run([sys.executable, "01_preprocess.py"], check=True)
        subprocess.run([sys.executable, "03_train_model.py"], check=True)
        load_models()
    background_tasks.add_task(_job)
    return {"message": "재학습 시작 (백그라운드)"}

@app.get("/model/info", summary="모델 메타데이터", tags=["모델"])
def model_info():
    if not store.metadata: raise HTTPException(503, "모델 없음")
    return store.metadata
