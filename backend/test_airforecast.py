import requests

API_KEY = "1046200dafe9143f9410798b3638c5353c7004949298293d317032ed3e415c85"

url = "http://apis.data.go.kr/B552584/ArpltnInforInqireSvc/getMinuDustFrcstDspth"
params = {
    "serviceKey": API_KEY,
    "returnType": "json",
    "numOfRows": 5,
    "pageNo": 1,
    "searchDate": "2026-04-07",
    "InformCode": "PM25",
}

r = requests.get(url, params=params, timeout=10)
print(f"상태코드: {r.status_code}")
print(f"응답: {r.text[:500]}")