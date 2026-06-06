import requests, json

url = 'http://127.0.0.1:8000/api/v1/agent/process'
payload = {"prompt": "你好", "session_id": None}
headers = {'Content-Type': 'application/json'}
response = requests.post(url, json=payload, headers=headers)
print('Status:', response.status_code)
print('Response:', response.text)
