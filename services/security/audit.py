"""Audit Logging Middleware — tracks all API interactions for compliance.

Blueprint §8: Logs who did what, when, and from where.
Integrates with FastAPI middleware to capture request/response telemetry.
"""

from datetime import datetime, timezone
from typing import Any, Awaitable, Callable
import json
import logging
import time

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("canvasml.audit")
logger.setLevel(logging.INFO)

# In production, this should write to a secure append-only store
# like AWS CloudWatch, Azure Monitor, or an ELK stack.
_audit_handler = logging.StreamHandler()
_audit_handler.setFormatter(logging.Formatter('{"audit_event": %(message)s}'))
logger.addHandler(_audit_handler)


class AuditLoggingMiddleware(BaseHTTPMiddleware):
    """FastAPI middleware for compliance audit logging."""

    async def dispatch(self, request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        start_time = time.time()

        # Capture request context
        client_ip = request.client.host if request.client else "unknown"
        method = request.method
        path = request.url.path
        query_params = str(request.query_params)
        user_agent = request.headers.get("user-agent", "unknown")

        # Try to identify user (if auth middleware has run, or from token)
        user_id = "anonymous"
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            # For audit purposes, we might just extract the ID without validation
            # Real validation happens in the auth dependency
            user_id = "token_provided"

        # Process request
        try:
            response = await call_next(request)
            status_code = response.status_code
            error_detail = None
        except Exception as e:
            status_code = 500
            error_detail = str(e)
            raise e
        finally:
            process_time_ms = round((time.time() - start_time) * 1000, 2)

            # Build audit record
            audit_event = {
                "timestamp": datetime.utcnow().isoformat() + "Z",
                "event_type": "api_access",
                "actor": {
                    "user_id": getattr(request.state, "user_id", user_id),
                    "ip_address": client_ip,
                    "user_agent": user_agent,
                },
                "action": {
                    "method": method,
                    "path": path,
                    "query": query_params,
                },
                "outcome": {
                    "status_code": status_code,
                    "duration_ms": process_time_ms,
                    "success": 200 <= status_code < 400,
                }
            }

            if error_detail:
                audit_event["outcome"]["error"] = error_detail

            # Log the event
            logger.info(json.dumps(audit_event))

        return response
