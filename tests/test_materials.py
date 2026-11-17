"""Validate the files students download, using only the standard library."""
from __future__ import annotations

import csv
import hashlib
import importlib.util
import io
import json
import re
import tempfile
import unittest
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / "projeto-base"
PREFIX = "projeto-municipios/"
PACKAGES = ["modulo-03-inicio.zip", "modulo-04-inicio.zip"]


class PublishedMaterials(unittest.TestCase):
    def test_packages_match_published_checksums(self):
        checksums = {}
        for line in (ROOT / "SHA256SUMS").read_text(encoding="utf-8").splitlines():
            digest, filename = line.split("  ", 1)
            self.assertRegex(digest, r"^[a-f0-9]{64}$")
            checksums[filename] = digest
        self.assertEqual(set(checksums), {f"pacotes/{name}" for name in PACKAGES})
        for filename, expected in checksums.items():
            self.assertEqual(hashlib.sha256((ROOT / filename).read_bytes()).hexdigest(), expected)

    def test_initial_archive_matches_versioned_project(self):
        expected = {path.relative_to(BASE).as_posix(): path.read_bytes()
                    for path in BASE.rglob("*") if path.is_file()}
        with zipfile.ZipFile(ROOT / "pacotes" / PACKAGES[0]) as archive:
            self.assertIsNone(archive.testzip())
            self.assertEqual(set(archive.namelist()), {PREFIX + name for name in expected})
            for name, content in expected.items():
                self.assertEqual(archive.read(PREFIX + name), content, name)
            self.assertNotIn(PREFIX + "index.html", archive.namelist())
            self.assertNotIn(PREFIX + "CLAUDE.md", archive.namelist())
            self.assertNotIn(PREFIX + "AGENTS.md", archive.namelist())

    def test_restart_keeps_data_and_tutor_but_adds_reference_page(self):
        with zipfile.ZipFile(ROOT / "pacotes" / PACKAGES[0]) as initial:
            with zipfile.ZipFile(ROOT / "pacotes" / PACKAGES[1]) as restart:
                self.assertIsNone(restart.testzip())
                self.assertEqual(set(restart.namelist()), set(initial.namelist()) | {PREFIX + "index.html"})
                for filename in initial.namelist():
                    if filename != PREFIX + "LEIA-ME.txt":
                        self.assertEqual(initial.read(filename), restart.read(filename), filename)
                self.assertIn(b"<svg", restart.read(PREFIX + "index.html"))

    def test_archives_only_contain_safe_student_project_paths(self):
        for name in PACKAGES:
            with zipfile.ZipFile(ROOT / "pacotes" / name) as archive:
                for filename in archive.namelist():
                    entry = PurePosixPath(filename)
                    self.assertTrue(filename.startswith(PREFIX), filename)
                    self.assertFalse(entry.is_absolute(), filename)
                    self.assertNotIn("..", entry.parts)
                    self.assertNotIn("\\", filename)
                    self.assertNotIn(".git", entry.parts)
                    self.assertNotIn("gabarito", filename.lower())

    def test_data_keys_units_years_and_missing_values_are_preserved(self):
        data = BASE / "dados/municipios.csv"
        with data.open(encoding="utf-8", newline="") as handle:
            rows = list(csv.DictReader(handle))
        metadata = json.loads((BASE / "dados/fontes.json").read_text(encoding="utf-8"))
        self.assertEqual(len(rows), 5570)
        self.assertEqual(len({row["codigo_ibge"] for row in rows}), 5570)
        self.assertEqual(hashlib.sha256(data.read_bytes()).hexdigest(), metadata["csv_sha256"])
        self.assertEqual(metadata["columns"]["populacao"]["year"], 2022)
        self.assertEqual(metadata["columns"]["pib_mil_reais"]["unit"], "mil reais correntes")
        self.assertEqual(metadata["columns"]["ideb_anos_iniciais"]["year"], 2023)
        for stage in ["iniciais", "finais"]:
            self.assertEqual(sum(row[f"ideb_anos_{stage}"] == "" for row in rows), metadata["missing_ideb"][stage])
        for row in rows:
            self.assertTrue(re.fullmatch(r"\d{7}", row["codigo_ibge"]))
            self.assertGreater(int(row["populacao"]), 0)
            for stage in ["iniciais", "finais"]:
                value = row[f"ideb_anos_{stage}"]
                if value:
                    self.assertTrue(0 <= float(value) <= 10)

    def test_tutor_copies_are_identical_and_starting_states_are_correct(self):
        claude = BASE / ".claude/skills/tutor"
        agents = BASE / ".agents/skills/tutor"
        for path in claude.rglob("*"):
            if path.is_file():
                self.assertEqual(path.read_bytes(), (agents / path.relative_to(claude)).read_bytes())
        spec = importlib.util.spec_from_file_location("tutor", claude / "scripts/verificar.py")
        tutor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tutor)
        for name, expected in zip(PACKAGES, ["nao_iniciado", "feito"]):
            with tempfile.TemporaryDirectory() as directory:
                with zipfile.ZipFile(ROOT / "pacotes" / name) as archive:
                    archive.extractall(directory)
                report = tutor.build_report(Path(directory) / "projeto-municipios", only=1)
                self.assertEqual(report["marcos"][0]["situacao"], expected)

    def test_published_surface_excludes_teacher_and_build_material(self):
        allowed = {"README.md", ".gitattributes", ".gitignore", "SHA256SUMS", ".github",
                   "pacotes", "projeto-base", "guias", "tests"}
        for path in ROOT.rglob("*"):
            relative = path.relative_to(ROOT)
            if ".git" in relative.parts or "__pycache__" in relative.parts:
                continue
            self.assertIn(relative.parts[0], allowed, str(relative))
            self.assertNotIn("gabarito", path.name.lower())


if __name__ == "__main__":
    unittest.main()
