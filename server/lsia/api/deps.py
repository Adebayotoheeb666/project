from typing import Annotated

from fastapi import Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from lsia.application.auth import require_teacher
from lsia.application.errors import Unauthenticated
from lsia.infrastructure.crypto import SchoolIdentity
from lsia.infrastructure.db import get_session
from lsia.infrastructure.models import Teacher
from lsia.infrastructure.security import decode_token

bearer = HTTPBearer(auto_error=False)


def school_identity(request: Request) -> SchoolIdentity:
    return request.app.state.identity


def current_teacher(
    creds: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
    session: Annotated[Session, Depends(get_session)],
) -> Teacher:
    if creds is None:
        raise Unauthenticated()
    try:
        payload = decode_token(creds.credentials)
    except Exception as exc:
        raise Unauthenticated("Session expired. Sign in again.") from exc
    return require_teacher(session, payload["sub"])
