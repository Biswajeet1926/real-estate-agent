import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel as FastAPIBaseModel
from core.config import settings
from graph.agent import app as langgraph_app

api = FastAPI(title="Real Estate Lead Agent")

# ---------------------------------------------------------
# 1. CORS MIDDLEWARE (Allows your website to talk to FastAPI)
# ---------------------------------------------------------
api.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows any website to connect. Safe for testing!
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Pydantic schema for the Web Interface
class ChatRequest(FastAPIBaseModel):
    user_message: str
    thread_id: str 

# ---------------------------------------------------------
# 2. THE WEB CHAT ROUTE (For your Website Widget)
# ---------------------------------------------------------
@api.post("/chat")
async def chat_endpoint(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    try:
        # Run the AI LangGraph state machine
        result = langgraph_app.invoke({"messages": [("user", req.user_message)]}, config)
        raw_content = result["messages"][-1].content
        
        if isinstance(raw_content, list):
            clean_text = " ".join([item.get("text", "") for item in raw_content if "text" in item])
        else:
            clean_text = raw_content
            
        return {"response": clean_text}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# ---------------------------------------------------------
# 3. THE TELEGRAM ROUTE (For your 24/7 Mobile Bot)
# ---------------------------------------------------------
@api.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    # Ignore edits, channel posts, or non-text updates
    if "message" not in data or "text" not in data["message"]:
        return {"status": "ignored"}
        
    chat_id = str(data["message"]["chat"]["id"])  # chat_id acts as the persistent thread_id
    user_text = data["message"]["text"]
    
    try:
        config = {"configurable": {"thread_id": chat_id}}
        result = langgraph_app.invoke({"messages": [("user", user_text)]}, config)
        raw_content = result["messages"][-1].content
        
        if isinstance(raw_content, list):
            clean_text = " ".join([item.get("text", "") for item in raw_content if "text" in item])
        else:
            clean_text = raw_content

        # Send the response back to the user via Telegram's API
        telegram_url = f"https://api.telegram.org/bot{settings.TELEGRAM_TOKEN}/sendMessage"
        payload = {
            "chat_id": chat_id,
            "text": clean_text
        }
        requests.post(telegram_url, json=payload)
        
        return {"status": "ok"}
        
    except Exception as e:
        print(f"Telegram Webhook Error: {e}")
        return {"status": "error"}
