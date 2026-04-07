import requests
import xml.etree.ElementTree as ET
from datetime import datetime

API_KEY = "1046200dafe9143f9410798b3638c5353c7004949298293d317032ed3e415c85"

now = datetime.now()
time_str = f"{now.strftime('%Y%m%d')}{(now.hour // 3) * 3:02d}"

# 대기정체지수 (황사 관련)
url = "https://apis.data.go.kr/1360000/LivingWthrIdxServiceV4/getAirDiffusionIdxV4"
params = {
    "serviceKey": API_KEY,
    "pageNo": 1,
    "numOfRows": 10,
    "dataType": "XML",
    "areaNo": "1100000000",  # 서울
    "time": time_str,
}

r = requests.get(url, params=params, timeout=10)
print(f"대기정체지수 상태코드: {r.status_code}")
print(f"응답: {r.text[:300]}")