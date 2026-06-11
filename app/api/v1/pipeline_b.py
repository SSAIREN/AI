from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any
from langchain_core.messages import HumanMessage
from app.pipelines.pipeline_b.graph import app as pipeline_b_graph

router = APIRouter()

class PipelineBInput(BaseModel):
    message: str

class PipelineBOutput(BaseModel):
    response: str
    detected_scam_types: List[str]
    urgency_level: str
    history: List[Dict[str, Any]]

@router.post("/run", response_model=PipelineBOutput)
async def run_pipeline_b(payload: PipelineBInput):
    try:
        # 1. Prepare LangGraph initial state using LangChain message classes
        initial_state = {
            "messages": [HumanMessage(content=payload.message)],
            "detected_scam_types": [],
            "urgency_level": "LOW"
        }
        
        # 2. Run LangGraph asynchronously
        result = await pipeline_b_graph.ainvoke(initial_state)
        
        # 3. Process the final state response
        messages = result.get("messages", [])
        last_message = messages[-1].content if messages else "No response generated."
        
        # Format history for easy JSON usage on client
        history = []
        for msg in messages:
            role = "user" if msg.type == "human" else "assistant"
            history.append({"role": role, "content": msg.content})
            
        return PipelineBOutput(
            response=last_message,
            detected_scam_types=result.get("detected_scam_types", []),
            urgency_level=result.get("urgency_level", "LOW"),
            history=history
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pipeline B error: {str(e)}")
