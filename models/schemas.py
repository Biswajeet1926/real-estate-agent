from pydantic import BaseModel, Field
from typing import Optional, TypedDict, Annotated
from langgraph.graph.message import add_messages

class RealEstateLead(BaseModel):
    name: Optional[str] = Field(None, description="The user's full name")
    phone: Optional[str] = Field(None, description="A valid 10-digit phone number")
    budget: Optional[int] = Field(None, description="The user's budget in USD")
    timeframe: Optional[str] = Field(None, description="When they want to buy (e.g., '1 month', 'ASAP')")

class AgentState(TypedDict):
    messages: Annotated[list, add_messages] 
    lead_data: RealEstateLead
    retry_count: int

# Add this to the bottom of real-estate-agent/models/schemas.py
class PropertySearch(BaseModel):
    query: str = Field(description="The natural language description of the property the user is looking for.")