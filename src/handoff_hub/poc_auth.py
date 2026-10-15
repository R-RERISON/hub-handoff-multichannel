"""Server-side role authorization and hashed local login (POC, not SSO)."""
from __future__ import annotations

import hashlib
import hmac
import re
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Header, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select

from handoff_hub.poc_db import AuthSession, AuthUser, HandoffSession, utc_now

PBKDF2_ITERATIONS = 600_000
HEARTBEAT_MAX_AGE = 40
ROLES = ("ADMIN", "SUPERVISOR", "OPERATOR", "AUDITOR")


def password_hash(password: str) -> str:
    salt = secrets.token_bytes(24)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, PBKDF2_ITERATIONS)
    return "$".join(("pbkdf2_sha256", str(PBKDF2_ITERATIONS), salt.hex(), digest.hex()))


def password_matches(password: str, encoded: str) -> bool:
    try:
        algorithm, count, salt_hex, digest_hex = encoded.split("$")
        if algorithm != "pbkdf2_sha256" or not 100_000 <= int(count) <= 1_000_000:
            return False
        actual = hashlib.pbkdf2_hmac(
            "sha256", password.encode(), bytes.fromhex(salt_hex), int(count)
        )
        return hmac.compare_digest(actual, bytes.fromhex(digest_hex))
    except (ValueError, TypeError):
        return False


def naive_utc() -> datetime:
    return datetime.now(UTC).replace(tzinfo=None)


@dataclass(frozen=True)
class Principal:
    username: str
    role: str
    operation_id: str
    operator_id: str | None
    user_id: str
    session_id: str | None = None


class LoginInput(BaseModel):
    username: str = Field(min_length=3, max_length=80)
    password: str = Field(min_length=1, max_length=256)


def identity(user: AuthUser) -> dict:
    return {"id": user.id, "username": user.username, "role": user.role,
            "operation_id": user.operation_id, "operator_id": user.operator_id}


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def get_principal(factory, authorization: str | None) -> Principal:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Autenticação individual obrigatória")
    token = authorization[7:].strip()
    if not 32 <= len(token) <= 256:
        raise HTTPException(401, "Sessão inválida")
    with factory() as db:
        session = db.scalar(select(AuthSession).where(
            AuthSession.token_hash == token_digest(token)
        ))
        if session is None or session.revoked or session.expires_at <= naive_utc():
            raise HTTPException(401, "Sessão expirada ou revogada")
        user = db.get(AuthUser, session.user_id)
        if user is None or not user.is_active or user.role not in ROLES:
            raise HTTPException(403, "Usuário desativado ou perfil desconhecido")
        return Principal(user.username, user.role, user.operation_id,
                         user.operator_id, user.id, session.id)


def require_owner(factory, handoff_id: str, operator_id: str) -> None:
    with factory() as db:
        h = db.get(HandoffSession, handoff_id)
        if h is None:
            raise HTTPException(404, "Atendimento inexistente")
        if h.operator_id != operator_id:
            raise HTTPException(403, "Atendimento pertence a outro operador")


def assert_access(factory, p: Principal, request: Request, payload: dict | None) -> None:
    path, method = request.url.path, request.method
    if p.role == "ADMIN":
        return
    if p.role == "SUPERVISOR":
        if method == "POST" and path in ("/v1/dispatch/offer", "/v1/dispatch/next"):
            raise HTTPException(403, "Distribuição manual desativada; use o serviço automático")
        if re.fullmatch(r"/v1/operators/[^/]+/(work|handoffs/[^/]+/close)", path):
            raise HTTPException(403, "Mesa exclusiva do operador")
        if path.endswith(("/accept", "/decline", "/transfer")) or (
            method == "POST" and path.endswith("/messages")
        ):
            raise HTTPException(403, "Supervisão não responde pelo operador")
        return
    if p.role == "AUDITOR":
        if method != "GET" or path == "/v1/outbox" or re.fullmatch(
            r"/v1/operators/[^/]+/work", path
        ):
            raise HTTPException(403, "Auditor tem acesso somente leitura")
        return
    if p.role != "OPERATOR" or not p.operator_id:
        raise HTTPException(403, "Perfil não permitido")
    oid = p.operator_id
    if method == "GET" and path == "/v1/queues":
        return
    if method == "GET" and path == "/v1/operators/{}/work".format(oid):
        return
    if method == "PATCH" and path == "/v1/operators/{}/presence".format(oid):
        return
    close = re.fullmatch(r"/v1/operators/([^/]+)/handoffs/([^/]+)/close", path)
    if close and method == "POST":
        if close.group(1) != oid:
            raise HTTPException(403, "Operador divergente")
        require_owner(factory, close.group(2), oid)
        return
    action = re.fullmatch(
        r"/v1/handoffs/([^/]+)/(accept|decline|transfer|messages|timeline)", path
    )
    if action:
        hid, suffix = action.groups()
        if suffix in ("accept", "decline", "transfer"):
            if method != "POST" or (payload or {}).get("operator_id") != oid:
                raise HTTPException(403, "Operador divergente")
        elif suffix == "messages":
            if method not in ("GET", "POST"):
                raise HTTPException(403, "Método não permitido")
            if method == "POST" and (
                (payload or {}).get("sender") != "OPERATOR"
                or (payload or {}).get("operator_id") != oid
            ):
                raise HTTPException(403, "Respostas apenas como operador responsável")
        elif suffix == "timeline" and method != "GET":
            raise HTTPException(403, "Método não permitido")
        require_owner(factory, hid, oid)
        return
    raise HTTPException(403, "Seu perfil não pode acessar este recurso")


def register_identity_endpoints(factory) -> APIRouter:
    router = APIRouter(prefix="/v1/auth", tags=["Identidade local"])
    @router.post("/login")
    def login(body: LoginInput):
        with factory() as db:
            user = db.scalar(select(AuthUser).where(AuthUser.username == body.username.lower()))
            if user is None or not user.is_active or not password_matches(
                body.password, user.password_hash
            ):
                raise HTTPException(401, "Usuário ou senha inválidos")
            token = secrets.token_urlsafe(48)
            db.add(AuthSession(
                user_id=user.id, token_hash=token_digest(token),
                expires_at=utc_now() + timedelta(hours=8), last_seen=utc_now(),
            ))
            db.commit()
            return {"access_token": token, "token_type": "bearer",
                    "expires_in": 28800, "user": identity(user)}

    @router.get("/me")
    def me(authorization: str | None = Header(default=None)):
        p = get_principal(factory, authorization)
        return {"id": p.user_id, "username": p.username, "role": p.role,
                "operation_id": p.operation_id, "operator_id": p.operator_id}

    @router.post("/heartbeat")
    def heartbeat(authorization: str | None = Header(default=None)):
        p = get_principal(factory, authorization)
        with factory.begin() as db:
            s = db.get(AuthSession, p.session_id)
            if s is None or s.revoked:
                raise HTTPException(401, "Sessão revogada")
            s.last_seen = utc_now()
        return {"status": "online"}

    @router.post("/logout")
    def logout(authorization: str | None = Header(default=None)):
        p = get_principal(factory, authorization)
        with factory.begin() as db:
            s = db.get(AuthSession, p.session_id)
            if s:
                s.revoked = True
        return {"status": "signed_out"}

    return router
