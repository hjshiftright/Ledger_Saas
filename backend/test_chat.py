import requests
headers = {"Authorization": "Bearer dev-user", "Content-Type": "application/json"}
body = {"message": "What is my net worth? Why is the message getting truncated at ₹?", "history": []}
try:
    resp = requests.post('http://localhost:8000/api/v1/chat', json=body, headers=headers)
    print("STATUS:", resp.status_code)
    print("JSON:", resp.text)
except Exception as e:
    print("ERROR:", e)
