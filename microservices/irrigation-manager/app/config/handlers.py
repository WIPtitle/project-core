from fastapi import Request
from fastapi.responses import JSONResponse
from app.exceptions.authorization_exception import AuthorizationException
from app.exceptions.not_found_exception import NotFoundException
from app.exceptions.valve_locked_exception import ValveLockedException


def get_exception_handlers():
    return [
        (AuthorizationException, lambda req, exc: JSONResponse(status_code=401, content={"detail": str(exc)})),
        (NotFoundException, lambda req, exc: JSONResponse(status_code=404, content={"detail": str(exc)})),
        (ValveLockedException, lambda req, exc: JSONResponse(status_code=423, content={"detail": str(exc)})),
    ]
