#!/usr/bin/env python3

"""Atualiza pom.xml do Trino Gateway para incluir dependencia H2."""

from __future__ import annotations

import sys
import xml.etree.ElementTree as ET

NS = {"maven": "http://maven.apache.org/POM/4.0.0"}
H2_NS = "{http://maven.apache.org/POM/4.0.0}"


def update_pom(pom_file: str = "gateway-ha/pom.xml") -> int:
    """Garante dependencia H2 2.2.224 no POM. Retorna 0 em sucesso, 1 em erro."""
    tree = ET.parse(pom_file)
    root = tree.getroot()

    dependencies = root.find(".//maven:dependencies", NS)
    if dependencies is None:
        print(f"ERROR: Could not find dependencies section in {pom_file}")
        return 1

    h2_exists = False
    for dep in dependencies.findall(".//maven:dependency", NS):
        group_id = dep.find("maven:groupId", NS)
        artifact_id = dep.find("maven:artifactId", NS)
        if group_id is not None and artifact_id is not None:
            if group_id.text == "com.h2database" and artifact_id.text == "h2":
                h2_exists = True
                version = dep.find("maven:version", NS)
                if version is not None:
                    version.text = "2.2.224"
                else:
                    version_elem = ET.SubElement(dep, f"{H2_NS}version")
                    version_elem.text = "2.2.224"
                print("INFO: H2 dependency already exists, updating version to 2.2.224")
                break

    if not h2_exists:
        h2_dep = ET.SubElement(dependencies, f"{H2_NS}dependency")
        group_id = ET.SubElement(h2_dep, f"{H2_NS}groupId")
        group_id.text = "com.h2database"
        artifact_id = ET.SubElement(h2_dep, f"{H2_NS}artifactId")
        artifact_id.text = "h2"
        version = ET.SubElement(h2_dep, f"{H2_NS}version")
        version.text = "2.2.224"
        print(f"SUCCESS: Added H2 dependency to {pom_file}")

    for dep in dependencies.findall(".//maven:dependency", NS):
        group_id = dep.find("maven:groupId", NS)
        artifact_id = dep.find("maven:artifactId", NS)
        if group_id is not None and artifact_id is not None:
            if group_id.text == "com.h2database" and artifact_id.text == "h2":
                scope = dep.find("maven:scope", NS)
                if scope is not None and scope.text != "compile":
                    scope.text = "compile"
                    print("INFO: Updated H2 scope to compile")
                break

    ET.register_namespace("", "http://maven.apache.org/POM/4.0.0")
    tree.write(pom_file, encoding="utf-8", xml_declaration=True)
    print(f"SUCCESS: Updated {pom_file}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = argv if argv is not None else sys.argv[1:]
    pom_file = args[0] if args else "gateway-ha/pom.xml"
    return update_pom(pom_file)


if __name__ == "__main__":
    sys.exit(main())
