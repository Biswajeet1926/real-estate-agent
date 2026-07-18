import json
import requests

def push_to_crm(lead_data: dict, tenant_id: str) -> bool:
    """
    Takes the validated lead dictionary from LangGraph and formats it 
    for an external CRM API or Webhook.
    """
    # 1. Format the payload exactly how the CRM expects it
    payload = {
        "tenant_id": tenant_id,
        "contact": {
            "first_name": lead_data.get("name", "").split(" ")[0],
            "full_name": lead_data.get("name"),
            "phone": lead_data.get("phone"),
            "custom_fields": {
                "budget": lead_data.get("budget"),
                "timeframe": lead_data.get("timeframe")
            }
        },
        "tags": ["AI_Qualified_Lead", "Web_Chat"]
    }

    # 2. In production, this will be an actual API POST request to GoHighLevel
    # For now, we will print it beautifully to the terminal to simulate the network transfer
    print("\n" + "="*50)
    print("🚀 [CRM ADAPTER] FIRING WEBHOOK TO EXTERNAL SYSTEM")
    print("="*50)
    print(json.dumps(payload, indent=2))
    print("="*50 + "\n")
    
    # 3. Return True to let LangGraph know the network request succeeded
    return True