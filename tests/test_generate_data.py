"""Testes do gerador de dados sinteticos em src/scripts/generate_data.py."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / "src" / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import generate_data as gd  # noqa: E402


def test_generate_tenant_id():
    tenant = gd.generate_tenant_id()
    assert tenant.startswith("T")
    assert 1 <= int(tenant[1:]) <= 50


def test_generate_status():
    assert gd.generate_status() in {"ATIVO", "INATIVO"}


def test_generate_valor():
    valor = gd.generate_valor()
    assert 10.0 <= valor <= 1000.0


def test_generate_date():
    start = datetime(2024, 1, 1)
    date_str = gd.generate_date(start, 10)
    parsed = datetime.strptime(date_str, "%Y-%m-%d")
    assert parsed >= start


def test_generate_document():
    doc = json.loads(gd.generate_document())
    assert doc["origem"] == "sintetico"
    assert doc["metadados"]["tipo"] in {"A", "B", "C"}


def test_generate_surrogate_key():
    assert gd.generate_surrogate_key(1) == "SK00000001"
    assert gd.generate_surrogate_key(42) == "SK00000042"


def test_generate_insert_statements(tmp_path):
    output = tmp_path / "out.sql"
    gd.generate_insert_statements(
        num_records=5,
        start_date="2024-01-01",
        num_days=30,
        batch_size=2,
        output_file=str(output),
    )
    content = output.read_text(encoding="utf-8")
    assert "INSERT INTO iceberg.analytics.tenant_info" in content
    assert "INSERT INTO iceberg.analytics.dados" in content
    assert content.count("INSERT INTO iceberg.analytics.dados") == 3
    assert "SK00000001" in content


def test_generate_large_dataset(tmp_path):
    output = tmp_path / "large.sql"
    with patch.object(gd, "generate_insert_statements") as mocked:
        gd.generate_large_dataset(output_file=str(output), size_gb=0.001)
        mocked.assert_called_once()
        kwargs = mocked.call_args.kwargs
        assert kwargs["output_file"] == str(output)
        assert kwargs["num_records"] > 0


def test_main_records(tmp_path, monkeypatch):
    output = tmp_path / "cli.sql"
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "generate_data.py",
            "--records",
            "3",
            "--batch",
            "2",
            "--output",
            str(output),
        ],
    )
    gd.main()
    assert output.exists()
    assert "INSERT INTO iceberg.analytics.dados" in output.read_text()


def test_main_size_gb(tmp_path, monkeypatch):
    output = tmp_path / "size.sql"
    monkeypatch.setattr(
        sys,
        "argv",
        ["generate_data.py", "--size-gb", "0.0001", "--output", str(output)],
    )
    with patch.object(gd, "generate_large_dataset") as mocked:
        gd.main()
        mocked.assert_called_once()
        assert mocked.call_args.kwargs["size_gb"] == 0.0001
