import logging

from fastapi import APIRouter, Request

from core.logging_utils import to_log_text
from models.schemas import ClientLogRequest, ok


router = APIRouter()


@router.post("/client-logs")
def ingest_client_log(payload: ClientLogRequest, request: Request):
    logger = logging.getLogger(f"wtcmd.client.{payload.source}")
    numeric_level = getattr(logging, payload.level.upper(), logging.INFO)
    client_host = request.client.host if request.client else "-"

    logger.log(
        numeric_level,
        (
            "Client event event=%s session_id=%s request_id=%s route=%s url=%s "
            "client=%s user_agent=%s created_at=%s message=%s context=%s"
        ),
        payload.event or "-",
        payload.session_id or "-",
        payload.request_id or "-",
        payload.route or "-",
        payload.url or "-",
        client_host,
        payload.user_agent or "-",
        payload.created_at or "-",
        payload.message,
        to_log_text(payload.context, default="{}"),
    )
    return ok({"accepted": True})