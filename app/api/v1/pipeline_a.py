from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage
from app.pipelines.pipeline_a.graph import app as pipeline_a_graph

router = APIRouter()

class PipelineAInput(BaseModel):
    message: str

class PipelineAOutput(BaseModel):
    response: str
    risk_score: float
    risk_level: str
    history: List[Dict[str, Any]]

@router.post("/run", response_model=PipelineAOutput)
async def run_pipeline_a(payload: PipelineAInput):
    try:
        # 1. Prepare LangGraph initial state using LangChain message classes
        initial_state = {
            "messages": [HumanMessage(content=payload.message)],
            "risk_score": 0.0,
            "risk_level": "LOW"
        }
        
        # 2. Run LangGraph asynchronously
        result = await pipeline_a_graph.ainvoke(initial_state)
        
        # 3. Process the final state response
        messages = result.get("messages", [])
        last_message = messages[-1].content if messages else "No response generated."
        
        # Format history for easy JSON usage on client
        history = []
        for msg in messages:
            role = "user" if msg.type == "human" else "assistant"
            history.append({"role": role, "content": msg.content})
            
        return PipelineAOutput(
            response=last_message,
            risk_score=result.get("risk_score", 0.0),
            risk_level=result.get("risk_level", "LOW"),
            history=history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline A error: {str(e)}")
