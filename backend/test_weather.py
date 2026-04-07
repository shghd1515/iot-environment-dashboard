import requests
import xml.etree.ElementTree as ET
from datetime import datetime

API_KEY = "1046200dafe9143f9410798b3638c5353c7004949298293d317032ed3e415c85"

now = datetime.now()
base_date = now.strftime("%Y%m%d")
base_time = "0500"

url = "http://apis.data.go.kr/1360000/VilageFcstInfoService_2.0/getVilageFcst"
params = {
    "serviceKey": API_KEY,
    "returnType": "XML",
    "numOfRows": 500,
    "pageNo": 1,
    "base_date": base_date,
    "base_time": base_time,
    "nx": 60,
    "ny": 127,
}

r = requests.get(url, params=params, timeout=10)
root = ET.fromstring(r.text)

categories = {
    "TMP": "온도(°C)",
    "REH": "습도(%)",
    "PTY": "강수형태",
    "SKY": "하늘상태",
    "WSD": "풍속(m/s)",
    "POP": "강수확률(%)"
}

results = {}
for item in root.findall(".//item"):
    cat  = item.findtext("category")
    time = item.findtext("fcstTime")
    val  = item.findtext("fcstValue")
    if cat in categories:
        if time not in results:
            results[time] = {}
        results[time][cat] = val

for time, vals in sorted(results.items())[:6]:
    print(f"\n{time}:")
    for cat, label in categories.items():
        if cat in vals:
            print(f"  {label}: {vals[cat]}")