import requests
import json

url = "http://localhost:5000/api/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "d6da470d75cf2c275418ea2028bd946ac1f8c0f21aad97bbae2b233869620857"
}
payload = {
    "model": "Qwen3.5-27B",
    "messages": [{"role": "user", "content": "你是谁"}],
    "max_tokens": 200,
    "temperature": 0.7
}

response = requests.post(url, headers=headers, json=payload, timeout=30)
print("Status Code:", response.status_code)
print("Response:")
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
