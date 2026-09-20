"""Testes do script add-h2-dependency."""

from __future__ import annotations

import sys
from pathlib import Path

GATEWAY = Path(__file__).resolve().parents[1] / "src" / "trino-gateway"
if str(GATEWAY) not in sys.path:
    sys.path.insert(0, str(GATEWAY))

import add_h2_dependency as h2  # noqa: E402

POM_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0">
  <modelVersion>4.0.0</modelVersion>
  <dependencies>
    {deps}
  </dependencies>
</project>
"""


def test_update_pom_adds_h2(tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text(POM_TEMPLATE.format(deps=""), encoding="utf-8")
    assert h2.update_pom(str(pom)) == 0
    content = pom.read_text(encoding="utf-8")
    assert "com.h2database" in content
    assert "2.2.224" in content


def test_update_pom_updates_existing_h2(tmp_path):
    deps = """
    <dependency>
      <groupId>com.h2database</groupId>
      <artifactId>h2</artifactId>
      <version>1.0.0</version>
      <scope>test</scope>
    </dependency>
    """
    pom = tmp_path / "pom.xml"
    pom.write_text(POM_TEMPLATE.format(deps=deps), encoding="utf-8")
    assert h2.update_pom(str(pom)) == 0
    content = pom.read_text(encoding="utf-8")
    assert "2.2.224" in content
    assert "compile" in content


def test_update_pom_missing_dependencies(tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text(
        '<?xml version="1.0"?><project xmlns="http://maven.apache.org/POM/4.0.0"></project>',
        encoding="utf-8",
    )
    assert h2.update_pom(str(pom)) == 1


def test_main_uses_argument(tmp_path):
    pom = tmp_path / "pom.xml"
    pom.write_text(POM_TEMPLATE.format(deps=""), encoding="utf-8")
    assert h2.main([str(pom)]) == 0
