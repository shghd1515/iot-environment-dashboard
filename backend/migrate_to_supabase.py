"""
migrate_to_supabase.py
노트북 MariaDB → Supabase PostgreSQL 데이터 이전
"""
import os
import pandas as pd
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()

# 노트북 MariaDB (소스)
mariadb_url = (
    f"mysql+pymysql://{os.getenv('DB_USER','root01')}:{os.getenv('DB_PASSWORD','00000')}"
    f"@{os.getenv('DB_HOST','192.168.101.2')}:{os.getenv('DB_PORT','3307')}"
    f"/{os.getenv('DB_NAME','sensor_db')}?charset=utf8mb4"
)

# Supabase PostgreSQL (목적지)
supabase_url = os.getenv("SUPABASE_DB_URL")

mariadb_engine  = create_engine(mariadb_url, pool_pre_ping=True)
supabase_engine = create_engine(supabase_url, pool_pre_ping=True)

def migrate():
    print("===== 데이터 이전 시작 =====\n")

    # sensor_combined 이전
    print("[1] sensor_combined 데이터 읽는 중...")
    df = pd.read_sql(
        "SELECT temperature, humidity, pm1, pm25, pm10, event, recorded_at FROM sensor_combined ORDER BY recorded_at ASC",
        mariadb_engine
    )
    print(f"  총 {len(df):,} 행 읽기 완료")

    print("[2] Supabase에 저장 중...")
    df.to_sql("sensor_combined", supabase_engine,
              if_exists="append", index=False, chunksize=500)
    print(f"  저장 완료!")

    # 확인
    with supabase_engine.connect() as conn:
        count = conn.execute(text("SELECT COUNT(*) FROM sensor_combined")).fetchone()[0]
    print(f"\n  Supabase sensor_combined 총 행수: {count:,}")
    print("\n===== 이전 완료 =====")

if __name__ == "__main__":
    migrate()