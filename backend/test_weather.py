import requests

API_KEY = "1046200dafe9143f9410798b3638c5353c7004949298293d317032ed3e415c85"

# 서울 기준 격자 좌표 (nx=60, ny=127)
url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"

from datetime import datetime, timedelta
now = datetime.now()
base_date = now.strftime("%Y%m%d")
base_time = "0500"  # 기준 시간

params = {
    "serviceKey": API_KEY,
    "returnType": "JSON",
    "numOfRows": 10,
    "pageNo": 1,
    "base_date": base_date,
    "base_time": base_time,
    "nx": 60,
    "ny": 127,
}

r = requests.get(url, params=params, timeout=10)
print(f"상태코드: {r.status_code}")
print(f"응답: {r.text[:500]}")