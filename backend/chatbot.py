"""
backend/06_chatbot.py
Gemini API 기반 챗봇 엔드포인트
04_fastapi_app.py 에 통합하여 사용

추가할 엔드포인트:
  POST /chat        → 챗봇 메시지 전송
  GET  /chat/sensor → 현재 센서 상태 (frontend용)
  GET  /chat/events → 이벤트 기록 조회
  GET  /chat/logs   → 자동제어 로그 조회
"""

import os
from datetime import datetime
from dotenv import load_dotenv
from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import create_engine, text
from google import genai
from google.genai import types

load_dotenv()

router = APIRouter(prefix="/chat", tags=["Gemini 챗봇"])

# ── Gemini 설정 ───────────────────────────────────────────────────────────────
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
gemini_model   = None
if GEMINI_API_KEY:
    gemini_client = genai.Client(api_key=GEMINI_API_KEY)
else:
    gemini_client = None

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

engine = get_engine()


# ── DB 유틸 ───────────────────────────────────────────────────────────────────
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


def get_hourly_data() -> list:
    sql = """SELECT 
                TO_CHAR(DATE_TRUNC('hour', recorded_at), 'YYYY-MM-DD HH24:00') as hour_label,
                ROUND(AVG(temperature)::numeric, 1) as avg_temp,
                ROUND(AVG(humidity)::numeric, 1)    as avg_humi,
                ROUND(AVG(pm25)::numeric, 1)        as avg_pm25
             FROM sensor_combined
             WHERE recorded_at >= NOW() - INTERVAL '24 hours'
             GROUP BY hour_label
             ORDER BY hour_label ASC"""
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql)).fetchall()
        return [{"hour": str(r[0]), "temperature": r[1],
                 "humidity": r[2], "pm25": r[3]} for r in rows]
    except Exception as e:
        print(f"[DB 오류] {e}")
    return []


def get_event_list() -> list:
    sql = """SELECT recorded_at, temperature, humidity, pm25, pm10, event
             FROM sensor_combined WHERE event IS NOT NULL
             ORDER BY recorded_at DESC LIMIT 20"""
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql)).fetchall()
        return [{"recorded_at": str(r[0]), "temperature": r[1],
                 "humidity": r[2], "pm25": r[3],
                 "pm10": r[4], "event": r[5]} for r in rows]
    except Exception as e:
        print(f"[DB 오류] {e}")
    return []


def get_control_logs() -> list:
    sql = """SELECT logged_at, hour_of_day, current_temp, current_humi,
                    current_pm25, target_temp, target_humidity, target_pm25, action
             FROM control_log
             ORDER BY logged_at DESC LIMIT 20"""
    try:
        with engine.connect() as conn:
            rows = conn.execute(text(sql)).fetchall()
        return [{"logged_at": str(r[0]), "hour": r[1],
                 "current_temp": r[2], "current_humi": r[3],
                 "current_pm25": r[4], "target_temp": r[5],
                 "target_humi": r[6], "target_pm25": r[7],
                 "action": r[8]} for r in rows]
    except Exception as e:
        print(f"[DB 오류] {e}")
    return []


def pm25_grade(val) -> str:
    if val is None: return "알수없음"
    if val < 15:    return "좋음"
    elif val < 35:  return "보통"
    elif val < 75:  return "나쁨"
    else:           return "매우나쁨"


# ── Gemini 컨텍스트 빌드 ─────────────────────────────────────────────────────
def build_context() -> str:
    s      = get_latest_sensor()
    events = get_event_list()[:5]
    hourly = get_hourly_data()
    now    = datetime.now()

    pm25_val   = s.get("pm25") or 0
    temp_val   = s.get("temperature") or 0
    humi_val   = s.get("humidity") or 0

    event_text = "\n".join(
        f"  {e['recorded_at']}: {e['event']} (온도 {e['temperature']}°C, PM2.5 {e['pm25']})"
        for e in events
    ) or "없음"

    # 이상 패턴 분석
    pattern_text = "데이터 없음"
    if len(hourly) >= 3:
        pm25_list  = [h["pm25"] for h in hourly if h["pm25"] is not None]
        temp_list  = [h["temperature"] for h in hourly if h["temperature"] is not None]
        if pm25_list:
            avg_pm25 = sum(pm25_list) / len(pm25_list)
            max_pm25 = max(pm25_list)
            min_pm25 = min(pm25_list)
            pattern_text = f"PM2.5 평균 {avg_pm25:.1f} / 최고 {max_pm25:.1f} / 최저 {min_pm25:.1f} μg/m³"
        if temp_list:
            avg_temp = sum(temp_list) / len(temp_list)
            pattern_text += f"\n  온도 평균 {avg_temp:.1f}°C (24시간 기준)"

    # 환경 개선 추천 힌트
    recommendations = []
    if pm25_val >= 35:
        recommendations.append("미세먼지가 나쁨 수준입니다. 환기를 권장합니다.")
    if pm25_val >= 75:
        recommendations.append("미세먼지가 매우 나쁨 수준입니다. 즉시 환기하고 마스크 착용을 권장합니다.")
    if temp_val >= 28:
        recommendations.append("실내 온도가 높습니다. 냉방 또는 환기를 권장합니다.")
    if temp_val <= 15:
        recommendations.append("실내 온도가 낮습니다. 난방을 권장합니다.")
    if humi_val >= 70:
        recommendations.append("습도가 높습니다. 제습기 사용 또는 환기를 권장합니다.")
    if humi_val <= 30:
        recommendations.append("습도가 낮습니다. 가습기 사용을 권장합니다.")
    if not recommendations:
        recommendations.append("현재 실내 환경은 전반적으로 양호합니다.")

    recommendation_text = "\n".join(f"  - {r}" for r in recommendations)

    return f"""
당신은 스마트홈 IoT 환경 관리 AI 어시스턴트입니다.
사용자의 실내 환경 데이터를 분석하고 친절하고 실용적으로 답변하세요.
답변은 한국어로 2~4문장으로 간결하게 작성하세요.
구체적인 수치를 언급하며 실질적인 행동을 추천하세요.

## 현재 실내 환경 ({now.strftime('%Y-%m-%d %H:%M')})
- 온도: {temp_val}°C
- 습도: {humi_val}%
- PM2.5: {pm25_val} μg/m³ ({pm25_grade(pm25_val)})
- PM10: {s.get('pm10', 'N/A')} μg/m³

## 24시간 환경 패턴 분석
{pattern_text}

## AI 환경 개선 추천
{recommendation_text}

## 최근 이벤트
{event_text}

## AI 자동제어 시스템 정보
- 매일 오후 2시 15분 환기 알람 자동 실행
- 1분마다 온도·습도·미세먼지 자동 제어 판단
- ML 모델로 시간대별 최적 환경값 예측
- 미세먼지 기준: 좋음(0~15) / 보통(15~35) / 나쁨(35~75) / 매우나쁨(75+)

## 답변 가이드
- 현재 수치를 언급하며 구체적으로 답변하세요
- 환기 필요 시 예상 효과를 수치로 제시하세요
- 이벤트 패턴이 있으면 언급하세요
- 행동 추천은 명확하고 실용적으로 하세요
""".strip()


# ── 스키마 ────────────────────────────────────────────────────────────────────
class ChatRequest(BaseModel):
    message: str
    history: list = []


# ── 이벤트 자동 감지 키워드 ──────────────────────────────────────────────────
EVENT_KEYWORDS = {
    "환기시작": ["환기 시작", "환기시작", "창문 열었", "창문 열어", "환기할게"],
    "환기종료": ["환기 끝", "환기종료", "창문 닫았", "창문 닫아", "환기 완료"],
    "요리시작": ["요리 시작", "요리시작", "요리 중", "밥 하"],
    "요리종료": ["요리 끝", "요리 완료", "요리종료"],
    "청소시작": ["청소 시작", "청소기", "청소시작"],
    "청소종료": ["청소 끝", "청소 완료", "청소종료"],
    "외출":     ["외출", "나가요", "나갑니다"],
    "귀가":     ["귀가", "들어왔", "돌아왔"],
}

def detect_event(message: str):
    msg = message.lower()
    for event_name, keywords in EVENT_KEYWORDS.items():
        for kw in keywords:
            if kw in msg:
                return event_name
    return None

def record_event_db(event_name: str):
    try:
        with engine.connect() as conn:
            conn.execute(text(
                "UPDATE sensor_combined SET event = :e "
                "WHERE recorded_at = (SELECT MAX(recorded_at) FROM "
                "(SELECT recorded_at FROM sensor_combined) AS t)"
            ), {"e": event_name})
            conn.commit()
    except Exception as e:
        print(f"[이벤트 오류] {e}")


# ── 엔드포인트 ────────────────────────────────────────────────────────────────

@router.post("", summary="챗봇 메시지 전송")
def chat(req: ChatRequest):
    # 이벤트 자동 감지
    detected_event = detect_event(req.message)
    if detected_event:
        record_event_db(detected_event)

    # 대화 히스토리 구성
    history_text = ""
    if req.history:
        history_text = "\n## 이전 대화\n"
        for h in req.history[-6:]:
            role = "사용자" if h.get("role") == "user" else "AI"
            history_text += f"{role}: {h.get('content','')}\n"

    prompt = f"""
{build_context()}
{history_text}

## 사용자 질문
{req.message}

답변:""".strip()

    if not gemini_client:
        answer = "Gemini API 키가 설정되지 않았습니다. .env 파일을 확인해주세요."
    else:
        try:
            response = gemini_client.models.generate_content(
                model="models/gemini-2.0-flash",
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=1024,
                )
            )
            answer = response.text.strip()
        except Exception as e:
            err = str(e)
            print(f"[Gemini 오류] {err}")
            if "429" in err or "RESOURCE_EXHAUSTED" in err or "quota" in err.lower():
                answer = "현재 AI 서비스 이용량이 초과됐습니다. 잠시 후 다시 시도해주세요. (보통 1분 후 자동 복구됩니다)"
            elif "404" in err or "not found" in err.lower():
                answer = "AI 모델 연결에 문제가 발생했습니다. 서버 관리자에게 문의해주세요."
            elif "API" in err or "key" in err.lower():
                answer = "Gemini API 키를 확인해주세요. .env 파일의 GEMINI_API_KEY를 확인해주세요."
            else:
                answer = "일시적인 오류가 발생했습니다. 잠시 후 다시 시도해주세요."

    return {
        "answer":         answer,
        "detected_event": detected_event,
        "timestamp":      datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@router.get("/sensor", summary="현재 센서 상태 + 시간대별 데이터")
def get_sensor_data():
    sensor  = get_latest_sensor()
    hourly  = get_hourly_data()
    pm25_val = sensor.get("pm25") or 0
    return {
        "current":    sensor,
        "pm25_grade": pm25_grade(pm25_val),
        "hourly":     hourly,
    }


@router.get("/events", summary="이벤트 기록 조회")
def get_events():
    return get_event_list()


@router.get("/logs", summary="자동제어 로그 조회")
def get_logs():
    return get_control_logs()
