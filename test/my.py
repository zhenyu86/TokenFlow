import requests

url = "http://10.100.2.27:30000/v1/chat/completions"
headers = {
    "Content-Type": "application/json",
    "Authorization": "Bearer token-abc123"
}
payload = {
    "model": "Qwen3.5-27B",
    "messages": [{"role": "user", "content": "你是谁"}],
    "max_tokens": 200,
    "temperature": 0.7
}

response = requests.post(url, headers=headers, json=payload, timeout=30)
result = response.json()

message = result["choices"][0]["message"]
reply = message.get("content") or message.get("reasoning_content", "")
usage = result["usage"]

print(reply)
print("prompt_tokens:",usage["prompt_tokens"])
print("completion_tokens:",usage["completion_tokens"])
print("total_tokens",usage["total_tokens"])