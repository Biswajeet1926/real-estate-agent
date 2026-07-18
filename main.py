import requests
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from pydantic import BaseModel as FastAPIBaseModel
from core.config import settings

api = FastAPI(title="Real Estate Lead Agent")

# ---------------------------------------------------------
# BRUTE-FORCE CORS INTERCEPTOR
# ---------------------------------------------------------
@api.middleware("http")
async def add_custom_cors_headers(request: Request, call_next):
    # Intercept the browser's preflight check and force an "OK" with open headers
    if request.method == "OPTIONS":
        response = JSONResponse(content="OK")
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS, DELETE, PUT"
        response.headers["Access-Control-Allow-Headers"] = "*"
        return response

    # Process normal requests and attach open headers to the response
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers["Access-Control-Allow-Methods"] = "POST, GET, OPTIONS, DELETE, PUT"
    response.headers["Access-Control-Allow-Headers"] = "*"
    return response

# Import LangGraph app AFTER the middleware
from graph.agent import app as langgraph_app

class ChatRequest(FastAPIBaseModel):
    user_message: str
    thread_id: str 

# ---------------------------------------------------------
# THE WEB CHAT ROUTE
# ---------------------------------------------------------
@api.post("/chat")
async def chat_endpoint(req: ChatRequest):
    config = {"configurable": {"thread_id": req.thread_id}}
    try:
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
# THE TELEGRAM ROUTE
# ---------------------------------------------------------
@api.post("/telegram")
async def telegram_webhook(request: Request):
    data = await request.json()
    
    if "message" not in data or "text" not in data["message"]:
        return {"status": "ignored"}
        
    chat_id = str(data["message"]["chat"]["id"])
    user_text = data["message"]["text"]
    
    try:
        config = {"configurable": {"thread_id": chat_id}}
        result = langgraph_app.invoke({"messages": [("user", user_text)]}, config)
        raw_content = result["messages"][-1].content
        
        if isinstance(raw_content, list):
            clean_text = " ".join([item.get("text", "") for item in raw_content if "text" in item])
        else:
            clean_text = raw_content

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