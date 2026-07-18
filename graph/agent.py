import os
from services.crm_adapter import push_to_crm
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import ToolMessage
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from models.schemas import AgentState, RealEstateLead, PropertySearch
from services.rag_engine import search_properties

# Import the state and schema from your models folder
from models.schemas import AgentState, RealEstateLead
from dotenv import load_dotenv
from models.schemas import AgentState, RealEstateLead

# Initialize the memory saver
memory = MemorySaver()


# 1. Initialize Gemini

load_dotenv()  # Load environment variables from .env file
llm = ChatGoogleGenerativeAI(
    model="gemini-3.1-flash-lite", 
    temperature=0, 
    api_key=os.getenv("GEMINI_API_KEY")
)
llm_with_tools = llm.bind_tools([RealEstateLead, PropertySearch])

# 2. Define the Nodes
def call_model(state: AgentState):
    response = llm_with_tools.invoke(state["messages"])
    return {"messages": [response]}

def validate_lead(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    retry_count = state.get("retry_count", 0)

    # 1. If it's just a normal chat message, do nothing
    if not hasattr(last_message, 'tool_calls') or not last_message.tool_calls:
        return {"retry_count": retry_count}

    tool_call = last_message.tool_calls[0]
    tool_name = tool_call["name"]
    args = tool_call["args"]

    # ==========================================
    # TOOL 1: THE RAG PROPERTY SEARCH
    # ==========================================
    if tool_name == "PropertySearch":
        query = args.get("query", "")
        # Call your RAG engine service
        search_results = search_properties(query, tenant_id="brokerage_pilot_001")
        
        # Return the database results back to Gemini so it can read them to the user
        return {
            "messages": [ToolMessage(
                tool_call_id=tool_call["id"],
                name=tool_name,
                content=f"Database Results:\n{search_results}\n\nPresent these options to the user naturally, then ask if they want to book a viewing."
            )],
            "retry_count": retry_count
        }

    # ==========================================
    # TOOL 2: THE LEAD EXTRACTION
    # ==========================================
    elif tool_name == "RealEstateLead":
        missing_fields = []
        if not args.get("name"): missing_fields.append("name")
        if not args.get("phone"): missing_fields.append("phone")
        if not args.get("budget"): missing_fields.append("budget")
        if not args.get("timeframe"): missing_fields.append("timeframe")

        if missing_fields:
            retry_count += 1
            if retry_count >= 3:
                return {
                    "messages": [ToolMessage(tool_call_id=tool_call["id"], name=tool_name, content="SYSTEM_ERROR: Max retries reached.")],
                    "retry_count": retry_count
                }
            return {
                "messages": [ToolMessage(tool_call_id=tool_call["id"], name=tool_name, content=f"Validation failed. Missing fields: {', '.join(missing_fields)}. Ask user.")],
                "retry_count": retry_count
            }

        return {
            "messages": [ToolMessage(tool_call_id=tool_call["id"], name=tool_name, content="Success! All lead data extracted.")],
            "lead_data": args, 
            "retry_count": retry_count
        }
    
def human_handoff(state: AgentState):
    return {"messages": [("assistant", "I want to make sure we get this perfect. I'm having one of our senior agents review this and call you shortly.")]}

def save_to_crm(state: AgentState):
    # 1. Extract the pristine data that passed Pydantic validation
    lead_data = state.get("lead_data", {})
    
    # 2. Push it to the adapter. 
    # Hardcoding a tenant_id for the prototype. In SaaS mode, this comes from the request header.
    success = push_to_crm(lead_data, tenant_id="brokerage_pilot_001")
    
    # 3. Respond to the user based on the network result
    if success:
        return {"messages": [("assistant", "Perfect, I have all your details safely stored. One of our senior agents will review your criteria and reach out shortly!")]}
    else:
        return {"messages": [("assistant", "I have your details, but our booking system is momentarily busy. We will contact you soon.")]}
# 3. Define the Router
def route_after_validation(state: AgentState):
    messages = state["messages"]
    last_message = messages[-1]
    retry_count = state.get("retry_count", 0)

    # 1. CIRCUIT BREAKER: If we tried to extract data 3 times and failed, hand off to a human
    if retry_count >= 3:
        return "human_handoff"
        
    # 2. CHAT ROUTE: If the last message is just normal text from Gemini (no tool calls),
    # stop the graph here and send the text back to the user.
    if hasattr(last_message, 'tool_calls') and not last_message.tool_calls:
        return "end"
    
    # 3. SUCCESS ROUTE: If validation succeeded and appended a successful ToolMessage
    if isinstance(last_message, ToolMessage) and "Success" in last_message.content:
        return "save_to_crm"
        
    # 4. RETRY ROUTE: If it's a ToolMessage containing a validation error, go back to agent
    return "agent"

# 4. Compile the Graph
workflow = StateGraph(AgentState)

workflow.add_node("agent", call_model)
workflow.add_node("validate", validate_lead)
workflow.add_node("human_handoff", human_handoff)
workflow.add_node("save_to_crm", save_to_crm)

workflow.set_entry_point("agent")
workflow.add_edge("agent", "validate")
# Update the conditional edges section at the bottom of graph/agent.py
workflow.add_conditional_edges(
    "validate", 
    route_after_validation,
    {
        "human_handoff": "human_handoff",
        "save_to_crm": "save_to_crm",
        "agent": "agent",
        "end": END  # <--- Add this mapping here!
    }
)
workflow.add_edge("human_handoff", END)
workflow.add_edge("save_to_crm", END)

app = workflow.compile(checkpointer=memory)