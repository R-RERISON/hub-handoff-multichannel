"""Single-command local dev launcher for the Handoff Hub SQLite POC.

Starts FastAPI and Vite in one console, provisions missing dependencies,
keeps the POC key on the local machine, and shuts down children together.
Run via start.cmd on Windows, or python scripts/dev.py elsewhere.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import secrets
import shutil
import signal
import socket
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
VENV = ROOT / ".venv"
VENV_PYTHON = VENV / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
SETUP_MARKER = VENV / ".handoff-setup.json"
LOCAL_KEY_FILE = ROOT / "data" / ".poc-key"
BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:5173"
PLACEHOLDER_KEYS = {
    "SUA-CHAVE-LOCAL-FORTE",
    "INSIRA-UMA-CHAVE-LOCAL-ALEATORIA",
    "CHANGE_THIS_TO_RANDOM_LOCAL_KEY",
    "SUBSTITUA-POR-CHAVE-LOCAL",
}


class LauncherError(Exception):
    """Expected setup or runtime error with a helpful message."""


def report(message: str) -> None:
    print(f"[Handoff] {message}", flush=True)


def fingerprint(paths: list[Path]) -> str:
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.name.encode())
        digest.update(path.read_bytes())
    return digest.hexdigest()


def run_command(argv: list[str], cwd: Path = ROOT) -> None:
    report("Executando: " + " ".join(argv))
    try:
        subprocess.run(argv, cwd=cwd, check=True)
    except FileNotFoundError as exc:
        raise LauncherError(f"Ferramenta nao encontrada: {argv[0]}") from exc
    except subprocess.CalledProcessError as exc:
        raise LauncherError(f"Comando falhou (codigo {exc.returncode}): {' '.join(argv)}") from exc


def ensure_dependencies() -> tuple[str, str]:
    if sys.version_info < (3, 12):
        raise LauncherError("Python 3.12 ou superior e necessario (verifique: python --version).")
    if not (WEB / "package.json").is_file():
        raise LauncherError("Diretorio web/package.json nao encontrado. Execute da copia completa do repo.")
    npm = shutil.which("npm.cmd") if os.name == "nt" else shutil.which("npm")
    npm = npm or shutil.which("npm")
    if not npm:
        raise LauncherError("Node.js/npm nao instalado ou fora do PATH. Instale Node.js e reabra o terminal.")
    if not VENV_PYTHON.exists():
        report("Criando ambiente virtual Python (.venv)...")
        run_command([sys.executable, "-m", "venv", str(VENV)])
    backend_hash = fingerprint([ROOT / "pyproject.toml"])
    frontend_hash = fingerprint([WEB / "package.json"])
    try:
        saved = json.loads(SETUP_MARKER.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        saved = {}
    if saved.get("backend") != backend_hash:
        report("Sincronizando dependencias Python...")
        run_command([str(VENV_PYTHON), "-m", "pip", "install", "-e", ".[dev]"])
        saved["backend"] = backend_hash
        SETUP_MARKER.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    else:
        report("Dependencias Python ja preparadas.")
    if saved.get("frontend") != frontend_hash or not (WEB / "node_modules").is_dir():
        report("Sincronizando dependencias React/Vite...")
        run_command([npm, "install", "--no-audit", "--no-fund"], cwd=WEB)
        saved["frontend"] = frontend_hash
        SETUP_MARKER.write_text(json.dumps(saved, indent=2), encoding="utf-8")
    else:
        report("Dependencias frontend ja preparadas.")
    return str(VENV_PYTHON), npm


def local_key() -> str:
    supplied = os.environ.get("HANDOFF_POC_KEY", "").strip()
    if supplied and supplied not in PLACEHOLDER_KEYS:
        return supplied
    if supplied in PLACEHOLDER_KEYS:
        report("Chave de exemplo detectada; gerando uma chave local em seu lugar.")
    LOCAL_KEY_FILE.parent.mkdir(parents=True, exist_ok=True)
    if LOCAL_KEY_FILE.exists():
        key = LOCAL_KEY_FILE.read_text(encoding="utf-8").strip()
        if key:
            return key
    key = secrets.token_urlsafe(32)
    try:
        fd = os.open(LOCAL_KEY_FILE, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            file.write(key + "\n")
    except OSError as exc:
        raise LauncherError("Nao foi possivel gravar a chave local em data/.poc-key") from exc
    return key


def port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as conn:
        conn.settimeout(0.5)
        return conn.connect_ex(("127.0.0.1", port)) == 0


def pipe_output(proc: subprocess.Popen[str], label: str) -> None:
    if not proc.stdout:
        return
    try:
        for line in proc.stdout:
            print(f"[{label}] {line.rstrip()}", flush=True)
    except (OSError, ValueError):
        pass


def spawn(label: str, cmd: list[str], cwd: Path, env: dict[str, str]) -> subprocess.Popen[str]:
    kwargs: dict = {"cwd": cwd, "env": env, "stdin": subprocess.DEVNULL,
                    "stdout": subprocess.PIPE, "stderr": subprocess.STDOUT,
                    "encoding": "utf-8", "errors": "replace", "bufsize": 1}
    if os.name == "nt":
        kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP
    else:
        kwargs["start_new_session"] = True
    try:
        proc = subprocess.Popen(cmd, **kwargs)
    except OSError as exc:
        raise LauncherError(f"Nao foi possivel iniciar {label}: {exc}") from exc
    threading.Thread(target=pipe_output, args=(proc, label), daemon=True).start()
    return proc


def service_ready(url: str) -> bool:
    # Ignore proxy settings, as both services listen on localhost only.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with opener.open(url, timeout=1.0) as response:
            return 200 <= response.status < 300
    except (urllib.error.URLError, TimeoutError, OSError):
        return False


def wait_for_services(children: list[tuple[str, subprocess.Popen[str]]], timeout: float = 45.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        for label, proc in children:
            if proc.poll() is not None:
                raise LauncherError(f"{label} encerrou antes de iniciar (codigo {proc.returncode}).")
        if service_ready(BACKEND_URL + "/health/live") and service_ready(FRONTEND_URL + "/"):
            return
        time.sleep(0.35)
    raise LauncherError("API ou frontend nao iniciou. Consulte as mensagens [API] e [WEB] acima.")


def stop_children(children: list[tuple[str, subprocess.Popen[str]]]) -> None:
    for label, proc in reversed(children):
        if proc.poll() is not None:
            continue
        report(f"Encerrando {label}...")
        if os.name == "nt":
            # /T also stops Uvicorn --reload and npm/Vite descendants.
            subprocess.run(["taskkill", "/PID", str(proc.pid), "/T", "/F"],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=False)
        else:
            try:
                os.killpg(proc.pid, signal.SIGTERM)
            except ProcessLookupError:
                pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gerenciador local do Handoff Hub POC")
    parser.add_argument("--setup-only", action="store_true", help="Instala dependencias e sai")
    parser.add_argument("--setup-users", action="store_true", help="Provisiona usuarios locais e sai")
    parser.add_argument("--reset-users", action="store_true", help="Rotaciona senhas locais")
    parser.add_argument("--check", action="store_true", help="Executa pytest, Ruff e build do frontend")
    parser.add_argument("--no-browser", action="store_true", help="Nao abre navegador automaticamente")
    args = parser.parse_args(argv)
    children: list[tuple[str, subprocess.Popen[str]]] = []
    try:
        python, npm = ensure_dependencies()
        if args.setup_users or args.reset_users:
            cmd = [python, "-m", "handoff_hub.seed_demo_auth"]
            if args.reset_users:
                cmd.append("--reset-users")
            run_command(cmd)
            return 0
        if args.check:
            run_command([python, "-m", "pytest", "-q"])
            run_command([python, "-m", "ruff", "check", "src", "tests"])
            run_command([npm, "run", "build"], cwd=WEB)
            report("Pytest, Ruff e frontend build aprovados.")
            return 0
        if args.setup_only:
            report("Setup concluido. Execute start.cmd para iniciar os servicos.")
            return 0
        for name, port in [("FastAPI", 8000), ("Vite", 5173)]:
            if port_in_use(port):
                raise LauncherError(f"Porta {port} ocupada ({name}). Encerre a instancia anterior e tente novamente.")
        # POC accounts and random passwords live ONLY in ignored local data.
        run_command([python, "-m", "handoff_hub.seed_demo_auth"])
        key = local_key()
        env = dict(os.environ)
        env["HANDOFF_POC_KEY"] = key
        env["PYTHONUNBUFFERED"] = "1"
        report("Iniciando API e interface no mesmo terminal...")
        children.append(("API", spawn("API", [python, "-m", "uvicorn", "handoff_hub.main:app",
                                             "--host", "127.0.0.1", "--port", "8000", "--reload"], ROOT, env)))
        children.append(("WEB", spawn("WEB", [npm, "run", "dev"], WEB, env)))
        wait_for_services(children)
        report("Servicos iniciados:")
        report("  Web: " + FRONTEND_URL)
        report("  API: " + BACKEND_URL + "/docs")
        report("  Login individual: admin.demo, supervisor.demo, auditor.demo, ana.demo, bruno.demo")
        report("  Senhas locais em data/demo-credentials.txt (arquivo fora do Git)")
        report("Use Ctrl+C para encerrar os dois servicos.")
        if not args.no_browser:
            webbrowser.open(FRONTEND_URL)
        while True:
            for label, proc in children:
                if proc.poll() is not None:
                    raise LauncherError(f"{label} encerrou inesperadamente (codigo {proc.returncode}).")
            time.sleep(0.5)
    except KeyboardInterrupt:
        report("Interrupcao solicitada pelo usuario.")
        return 0
    except LauncherError as exc:
        report("ERRO: " + str(exc))
        return 1
    finally:
        stop_children(children)


if __name__ == "__main__":
    raise SystemExit(main())
