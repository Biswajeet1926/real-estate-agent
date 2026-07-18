import requests

URL = "http://127.0.0.1:8000/chat"
# Using a fixed thread_id simulates a single ongoing user session
THREAD_ID = "brokerage_lead_test_101"

print("🤖 Chatbot API Test initialized. Type 'exit' to quit.\n")

while True:
    user_input = input("You: ")
    if user_input.lower() == 'exit':
        break
        
    # Send the payload matching your FastAPI ChatRequest schema
    payload = {
        "user_message": user_input,
        "thread_id": THREAD_ID
    }
    
    try:
        response = requests.post(URL, json=payload)
        data = response.json()
        print(f"Bot: {data['response']}\n")
    except Exception as e:
        print(f"Error connecting to server: {e}")