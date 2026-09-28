"""Firebase-token verification and the auth dependencies every route uses.

Every route that touches a user's own data depends on get_current_user;
admin-only routes depend on require_admin. Token verification is a thin,
overridable wrapper (_verify_token) so tests can stand in a fake decoded
token without hitting Firebase or needing real credentials.
"""

from pathlib import Path

import firebase_admin
from fastapi import Depends, Header, HTTPException
from firebase_admin import auth as firebase_auth
from firebase_admin import credentials
from sqlalchemy.orm import Session

from database import get_db, models

SERVICE_ACCOUNT_PATH = Path(__file__).resolve().parent.parent.parent / "firebase-service-account.json"

_app: firebase_admin.App | None = None


def _firebase_app() -> firebase_admin.App:
    """Initialize the Firebase Admin app once per process, lazily.

    Lazy so importing this module (e.g. for tests that monkeypatch
    _verify_token) never requires the service-account file to exist.

    Returns:
        The initialized Firebase app.

    Raises:
        FileNotFoundError: if the service-account file is missing.
    """
    global _app
    if _app is None:
        if not SERVICE_ACCOUNT_PATH.is_file():
            raise FileNotFoundError(
                f"{SERVICE_ACCOUNT_PATH} is missing -- download it from "
                "Firebase Console > Project settings > Service accounts."
            )
        _app = firebase_admin.initialize_app(credentials.Certificate(str(SERVICE_ACCOUNT_PATH)))
    return _app


def _verify_token(token: str) -> dict:
    """Verify a Firebase ID token. Isolated so tests can monkeypatch it.

    Args:
        token: The raw ID token from the Authorization header.

    Returns:
        The decoded token claims (at least "uid" and "email").

    Raises:
        Exception: whatever firebase_admin raises for an invalid/expired token.
    """
    _firebase_app()
    return firebase_auth.verify_id_token(token)


def get_current_user(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> models.User:
    """Resolve the request's Firebase token to a User row, provisioning one on first login.

    Args:
        authorization: The "Bearer <token>" header.
        db: Active database session.

    Returns:
        The matching (or newly created) User.

    Raises:
        HTTPException: 401 if the header is missing or the token is invalid.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")

    token = authorization.removeprefix("Bearer ").strip()
    try:
        decoded = _verify_token(token)
    except Exception as exc:
        raise HTTPException(status_code=401, detail="invalid or expired token") from exc

    uid = decoded["uid"]
    user = db.query(models.User).filter(models.User.firebase_uid == uid).one_or_none()
    if user is None:
        user = models.User(firebase_uid=uid, email=decoded.get("email", ""))
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    """Same as get_current_user, but 403s anyone who isn't an admin.

    Args:
        user: The already-authenticated user.

    Returns:
        The user, if they are an admin.

    Raises:
        HTTPException: 403 if the user's role is not "admin".
    """
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="admin only")
    return user
