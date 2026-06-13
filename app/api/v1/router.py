from fastapi import APIRouter
from app.api.v1 import pipeline_a

api_router = APIRouter()

# Register pipeline routes with distinct prefixes.
api_router.include_router(pipeline_a.router, prefix="/pipeline-a", tags=["Pipeline A"])
