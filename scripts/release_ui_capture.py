"""SPEC-006C-2: assisted, viewport-locked browser capture in real Edge/Chrome.

The operator signs in manually with synthetic TEMP credentials. This script
never reads passwords, tokens, cookies, message contents or screenshots.
Captured PNGs remain only in the disposable TEMP 006b4 lab; browser
observations are NOT evidence of production readiness or manual acceptance.

Optional local dependency (not added to the product): pip install playwright
Uses existing installed Windows Edge/Chrome channel; no browser download.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from fastapi.testclient import TestClient

from handoff_hub.poc_api import create_app
from scripts.lab_environment import LabSafetyError, validate_lab
from scripts.release_grant_toggle import (
    LabSafetyError as AttestationSafetyError,
    attest_running_backend,
    bearer,
    identities,
)
from scripts.release_ui_evidence_gate import (
    EVIDENCE_FOLDER,
    REQUIRED,
    _safe_folder,
    current_sha,
    initialize,
    inspect,
)

WEB_URL = "http://127.0.0.1:5173"
QA_KEY = "spec006c-browser-attestation-testclient-only"
LOGIN_BY_ROLE = {
    "AUDITOR": "auditor.demo",
    "SUPERVISOR": "supervisor.demo",
    "OPERATOR": "ana.demo",
}


def attested_lab(raw: str | Path):
    lab = validate_lab(raw)
    _, auditor_id = identities(lab.database)
    app = create_app(database_url=lab.database_url, api_key=QA_KEY)
    with TestClient(app, raise_server_exceptions=False) as client:
        headers = bearer(client, lab.credentials, "auditor.demo", auditor_id)
        # Read-only live API check; refuse stale/mismatched backend BEFORE opening.
        attest_running_backend(headers, auditor_id)
    return lab


def _username(gate: str, persona: str, queue: str) -> str:
    if gate == "UX-05" and persona == "OPERATOR" and queue == "n2":
        return "bruno.demo"
    return LOGIN_BY_ROLE[persona]


def _current_screen(page, required: tuple) -> dict:
    gate, persona, area, queue, width, height = required
    if not page.url.startswith(WEB_URL + "/"):
        raise LabSafetyError("Navegador nao esta no frontend LOCAL do Handoff")
    expected_route = "/supervisao/conversas" if area == "historico" else "/operador"
    if expected_route not in page.url:
        raise LabSafetyError("Rota inesperada para o cenario de captura")

    if area == "historico":
        control = page.locator("#verified-history-queue")
        if control.count() != 1 or not control.is_visible():
            raise LabSafetyError("Historico verificado nao esta aberto")
        selected = control.input_value()
        if queue and selected != queue:
            raise LabSafetyError("Fila selecionada diverge do cenario")
        if persona == "AUDITOR" and selected != "n1":
            raise LabSafetyError("Auditor deve estar na fila N1")
    else:
        if not page.locator(".operator-portal").is_visible():
            raise LabSafetyError("Mesa do Operador nao esta visivel")

    viewport = page.evaluate(
        "() => ({width:window.innerWidth,height:window.innerHeight,"
        "scrollWidth:document.documentElement.scrollWidth})"
    )
    if (viewport["width"], viewport["height"]) != (width, height):
        raise LabSafetyError("Viewport real difere da resolucao solicitada")
    return {
        "gate": gate, "persona": persona, "area": area,
        "queue": queue, "width": width, "height": height,
        "horizontal_overflow": viewport["scrollWidth"] > width,
    }


def capture_one(page, destination: Path, expected: tuple) -> dict:
    """Validate routing, role-specific UI, viewport; never overwrite evidence."""
    if destination.exists() or destination.is_symlink():
        raise LabSafetyError("Captura existente nao pode ser sobrescrita")
    check = _current_screen(page, expected)
    png = page.screenshot(full_page=False, animations="disabled")
    # Exclusive file creation guards against accidental overwrite and symlinks.
    with destination.open("xb") as fp:
        fp.write(png)
    return check


def capture(raw: str | Path, channel: str) -> dict:
    lab = attested_lab(raw)
    evidence_dir = _safe_folder(lab.directory)
    if not (evidence_dir / "manifest.json").exists():
        initialize(lab.directory)
    manifest = json.loads(
        (evidence_dir / "manifest.json").read_text(encoding="utf-8")
    )
    if manifest.get("source_sha") != current_sha():
        raise LabSafetyError("Manifesto nao pertence ao SHA local atual")
    rows = manifest.get("screenshots")
    if not isinstance(rows, list) or len(rows) != len(REQUIRED):
        raise LabSafetyError("Manifesto de capturas incompleto")
    slots = {
        (r["gate"], r["persona"], r["area"], r["queue"],
         r["width"], r["height"]): r["file"]
        for r in rows
    }
    if set(slots) != set(REQUIRED):
        raise LabSafetyError("Checklist de capturas nao corresponde ao contrato")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        raise LabSafetyError(
            "Instale a dependencia opcional local: python -m pip install playwright"
        ) from None

    # Group by persona for fewer manual logins. Explicitly new isolated browser
    # context per identity prevents a prior operator's bearer session leaking.
    ordered = sorted(REQUIRED, key=lambda r: (
        _username(r[0], r[1], r[3]), r[0], r[4], r[5], r[3],
    ))
    collected = []
    with sync_playwright() as driver:
        try:
            browser = driver.chromium.launch(channel=channel, headless=False)
        except Exception:
            raise LabSafetyError(
                "Browser Edge/Chrome local indisponivel; instale-o ou use --browser"
            ) from None
        context = None
        last_username = None
        try:
            for expected in ordered:
                gate, persona, area, queue, width, height = expected
                file_name = slots[expected]
                if (not isinstance(file_name, str)
                        or Path(file_name).name != file_name
                        or not file_name.endswith(".png")
                        or "/" in file_name or "\\" in file_name):
                    raise LabSafetyError("Nome de imagem invalido no manifesto")
                output = evidence_dir / file_name
                if output.is_symlink():
                    raise LabSafetyError("Symlink de screenshot proibido")
                if output.exists():
                    continue
                username = _username(gate, persona, queue)
                if username != last_username:
                    if context is not None:
                        context.close()
                    context = browser.new_context(
                        viewport={"width": width, "height": height},
                        device_scale_factor=1,
                    )
                    page = context.new_page()
                    page.goto(WEB_URL + "/inicio", wait_until="domcontentloaded")
                    last_username = username
                    print(
                        f"Perfil QA: {username} | autentique no navegador aberto "
                        "usando somente a credencial sintética TEMP."
                    )
                else:
                    page.set_viewport_size({"width": width, "height": height})

                # Browser is deliberately human-driven; no credential reads
                # or DOM transcription of protected messages take place.
                print(
                    f"{gate} | {persona} | {area} | fila {queue or 'N1'}"
                    f" | viewport {width}x{height}"
                )
                input("Navegue até a tela correta e pressione ENTER para capturar: ")
                observed = capture_one(page, output, expected)
                collected.append(observed)
                print(
                    "PNG capturado: "
                    + ("OVERFLOW_H_REVIEW_NEEDED" if observed["horizontal_overflow"]
                       else "GEOMETRY_CAPTURED")
                    + " (nao é aprovação visual)"
                )
        finally:
            if context is not None:
                context.close()
            browser.close()

    report = inspect(lab.directory)
    return {
        "result": report["result"],
        "screenshots_captured_this_run": len(collected),
        "horizontal_overflow_observed": sum(
            1 for item in collected if item["horizontal_overflow"]
        ),
        "source_sha": report["source_sha"],
        "present_captures": report["present_captures"],
        "missing_captures": report["missing_captures"],
        "manual_review": "NOT_RUN",
        "release_approved": False,
        "original_database_touched": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", required=True)
    parser.add_argument("--browser", choices=("msedge", "chrome"), default="msedge")
    args = parser.parse_args()
    try:
        output = capture(args.lab, args.browser)
    except (LabSafetyError, AttestationSafetyError) as exc:
        raise SystemExit("REPROVADO: " + str(exc)) from None
    except (KeyboardInterrupt, EOFError):
        raise SystemExit(
            "CANCELADO: capturas anteriores permanecem exclusivamente no TEMP"
        ) from None
    except (OSError, ValueError, KeyError, TypeError):
        raise SystemExit("REPROVADO: ambiente de captura nao esta pronto") from None
    print(json.dumps(output, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
