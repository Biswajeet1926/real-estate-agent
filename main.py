import requests
from fastapi import FastAPI, Request, HTTPException
from pydantic import BaseModel as FastAPIBaseModel
from core.config import settings
from graph.agent import app as langgraph_app

api = FastAPI(title="Real Estate Lead Agent")

# ... (Keep your existing /chat endpoint here for terminal testing) ...

# ---------------------------------------------------------
# 2. THE TELEGRAM ROUTE (100% Free Mobile Testing)
# ---------------------------------------------------------
@api.post("/telegram")
async def telegram_webhook(request: Request):
    # Telegram sends data as pure JSON
    data = await request.json()
    
    # Ignore edits or non-message events to prevent crashes
    if "message" not in data or "text" not in data["message"]:
        return {"status": "ignored"}
        
    chat_id = str(data["message"]["chat"]["id"]) # Use chat_id as the thread_id!
    user_text = data["message"]["text"]
    
    try:
        # 1. Run the AI graph
        config = {"configurable": {"thread_id": chat_id}}
        result = langgraph_app.invoke({"messages": [("user", user_text)]}, config)
        raw_content = result["messages"][-1].content
        
        # 2. Clean the output
        if isinstance(raw_content, list):
            clean_text = " ".join([item.get("text", "") for item in raw_content if "text" in item])
        else:
            clean_text = raw_content

        # 3. Send the reply back to the user via Telegram's API
        telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": clean_text
        }
        requests.post(telegram_url, json=payload)
        
        # FastAPI must return a 200 OK so Telegram knows we received it
        return {"status": "ok"}
        
    except Exception as e:
        print(f"Error: {e}")
        return {"status": "error"}