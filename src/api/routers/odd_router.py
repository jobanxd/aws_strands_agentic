# src/api/routers/odd_router.py

from fastapi import APIRouter, BackgroundTasks, HTTPException
from src.api.schemas.odd_schema import ODDRequest, ODDResponse, ODDStatusResponse
from src.api.services.odd_service import ODDService

router = APIRouter(prefix="/odd", tags=["ODD Review"])
service = ODDService()


@router.post("/trigger", response_model=ODDResponse)
async def trigger_odd_review(request: ODDRequest, background_tasks: BackgroundTasks):
    """
    Trigger an ODD review for a given party.
    Returns a process_id immediately — the pipeline runs in the background.
    Poll /odd/status/{process_id} to check progress.
    """
    process_id = await service.trigger(request.query)
    return ODDResponse(
        process_id=process_id,
        status="accepted",
        message="ODD review started. Poll /odd/status/{process_id} for updates.",
    )


@router.get("/status/{process_id}", response_model=ODDStatusResponse)
async def get_odd_status(process_id: str):
    """
    Poll the status of a running or completed ODD review.
    """
    result = await service.get_status(process_id)
    if not result:
        raise HTTPException(status_code=404, detail=f"Process ID {process_id} not found.")
    return result