#!/usr/bin/env python3

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SUBMODULE_DIR = ROOT / "submodules" / "Groq_API_Proxy_Service"


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def main() -> int:
    env = dict(os.environ)
    env_file_values = load_env_file(ROOT / ".env.local")
    for key, value in env_file_values.items():
        env.setdefault(key, value)

    if not env.get("GROQ_API_KEY") and not env.get("GROQ_API_KEYS"):
        print(
            "ERROR: GROQ_API_KEY or GROQ_API_KEYS is missing. Set it in the shell or in .env.local.",
            file=sys.stderr,
        )
        return 1

    venv_python = ROOT / ".venv" / "bin" / "python"
    python_bin = str(venv_python if venv_python.exists() else Path(sys.executable))

    cmd = [
        python_bin,
        "-m",
        "uvicorn",
        "api.app.main:app",
        "--host",
        env.get("APP_HOST", "127.0.0.1"),
        "--port",
        env.get("APP_PORT", "18010"),
    ]
    return subprocess.call(cmd, cwd=SUBMODULE_DIR, env=env)


if __name__ == "__main__":
    raise SystemExit(main())
