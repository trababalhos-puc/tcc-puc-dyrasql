"""Validacao basica dos scripts shell em src/scripts/."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "src" / "scripts"

SHELL_SCRIPTS = [
    "debug-ide-raw.sh",
    "init-iceberg.sh",
    "limpar-cache.sh",
    "monitor-routing.sh",
    "setup-gateway-backends-auto.sh",
    "GUIA_GERADOR.sh",
]


@pytest.mark.parametrize("script_name", SHELL_SCRIPTS)
def test_shell_script_exists_and_executable(script_name):
    path = SCRIPTS_DIR / script_name
    assert path.is_file()
    assert path.stat().st_mode & 0o111


@pytest.mark.parametrize("script_name", SHELL_SCRIPTS)
def test_shell_script_syntax(script_name):
    path = SCRIPTS_DIR / script_name
    result = subprocess.run(
        ["bash", "-n", str(path)],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr


def test_sql_init_files_exist():
    assert (SCRIPTS_DIR / "init-iceberg.sql").is_file()
    assert (SCRIPTS_DIR / "load-iceberg.sql").is_file()
