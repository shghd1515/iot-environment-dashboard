# main.py
# ================================================
# 스마트 빌딩 AIoT - 메인 실행 파일
# 라즈베리파이에서 실행하는 진입점
#
# 실행: python3 main.py
# ================================================

import os
import sys

# 프로젝트 루트 경로 설정
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from data.collector import DataCollector, setup_logging
from data.database.setup_db import create_database
from config.settings import DB_PATH


def main():
    # 1. 로그 시스템 초기화
    setup_logging()

    # 2. DB 없으면 자동 생성
    if not os.path.exists(DB_PATH):
        print("DB가 없어서 자동 생성합니다...")
        create_database()

    # 3. 데이터 수집 시작
    collector = DataCollector()
    collector.start()


if __name__ == "__main__":
    main()
