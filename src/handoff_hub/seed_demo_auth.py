"""Provision disposable POC users without committing or logging their passwords."""
from __future__ import annotations

import argparse
import os
import secrets
from pathlib import Path

from sqlalchemy import select

from handoff_hub.poc_auth import password_hash
from handoff_hub.poc_db import (
    AuthUser,
    Integration,
    Operation,
    Operator,
    Queue,
    QueueMembership,
    make_session_factory,
)

DEMO_USERS = (
    ("admin.demo", "ADMIN", None),
    ("supervisor.demo", "SUPERVISOR", None),
    ("auditor.demo", "AUDITOR", None),
    ("ana.demo", "OPERATOR", "op-ana"),
    ("bruno.demo", "OPERATOR", "op-bruno"),
)


def provision(factory, credential_file: Path, reset: bool = False) -> list[str]:
    credential_file.parent.mkdir(parents=True, exist_ok=True)
    generated: list[tuple[str, str, str]] = []
    with factory.begin() as db:
        if not db.get(Operation, "demo"):
            db.add(Operation(id="demo", name="Operação Demonstrativa"))
            db.flush()
        if not db.get(Integration, "demo-bot"):
            db.add(Integration(id="demo-bot", operation_id="demo",
                               name="Bot Simulado", channel="simulator"))
        for qid, name in (("n1", "Suporte N1"), ("n2", "Suporte N2")):
            if not db.get(Queue, qid):
                db.add(Queue(id=qid, operation_id="demo", name=name))
        for oid, name in (("op-ana", "Ana (demonstração)"),
                          ("op-bruno", "Bruno (demonstração)")):
            if not db.get(Operator, oid):
                db.add(Operator(id=oid, operation_id="demo", name=name,
                                presence="AVAILABLE", capacity=1))
        for qid, oid in (("n1", "op-ana"), ("n1", "op-bruno"), ("n2", "op-bruno")):
            if not db.get(QueueMembership, (qid, oid)):
                db.add(QueueMembership(queue_id=qid, operator_id=oid))
        db.flush()
        for username, role, operator_id in DEMO_USERS:
            account = db.scalar(select(AuthUser).where(AuthUser.username == username))
            if account is not None and not reset:
                continue
            password = secrets.token_urlsafe(18)
            if account is None:
                account = AuthUser(username=username, role=role, operation_id="demo",
                                   operator_id=operator_id, password_hash=password_hash(password))
                db.add(account)
            else:
                account.password_hash = password_hash(password)
                account.role = role
                account.operator_id = operator_id
            generated.append((username, role, password))
    if generated:
        # File only on the developer's machine, excluded from version control.
        if credential_file.exists() and not reset:
            # Avoid accidental overwrite of credentials for already-existing accounts.
            raise RuntimeError("Credenciais anteriores existem. Use --reset-users conscientemente.")
        lines = [
            "HANDOFF HUB — CREDENCIAIS DESCARTÁVEIS DA POC",
            "NÃO PUBLICAR, NÃO COMPARTILHAR, NÃO USAR EM AMBIENTE CORPORATIVO",
            "",
        ]
        lines += [": ".join((username+" ["+role+"]", password))
                  for username, role, password in generated]
        fd = os.open(credential_file, os.O_CREAT | os.O_TRUNC | os.O_WRONLY, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write("\n".join(lines)+"\n")
    return [account[0] for account in generated]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset-users", action="store_true")
    args = parser.parse_args()
    db_url = os.getenv("HANDOFF_DB_URL", "sqlite:///./data/handoff-poc.db")
    factory, engine = make_session_factory(db_url)
    try:
        names = provision(factory, Path("data/demo-credentials.txt"), args.reset_users)
        if names:
            print("Usuários provisionados:", ", ".join(names))
            print("Senhas geradas localmente: data/demo-credentials.txt")
        else:
            print("Usuários existentes preservados. Arquivo de senhas: data/demo-credentials.txt")
    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
