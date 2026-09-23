from __future__ import annotations

"""
NAME
    test_install_windows.py - Regression tests for Windows setup tooling.

DESCRIPTION
    Protects installer failure propagation, dependency ownership, launcher
    selection, and dependency-free generation from the canonical CLI EBNF.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[3]
INSTALLER_PATH = REPO_ROOT / "install_windows.ps1"
REQUIREMENTS_PATH = REPO_ROOT / "requirements-windows.txt"
GENERATOR_SOURCE_NAMES = (
    "gen_bridge_cli_parser.py",
    "bridge_cli_ebnf.txt",
    "bridge_cli_grammar_meta.json",
)
EXPECTED_REQUIREMENTS = {
    "python-can==4.6.1",
    "pyserial==3.5",
    "prompt-toolkit==3.0.53",
    "reportlab==5.0.1",
    "python-docx==1.2.0",
}
POWERSHELL_NAMES = ("powershell.exe", "powershell")
FAILURE_EXIT_CODE = 7


def _find_powershell() -> str | None:
    """Return an available Windows PowerShell executable, if present."""

    for name in POWERSHELL_NAMES:
        executable = shutil.which(name)
        if executable:
            return executable
    return None


@unittest.skipUnless(os.name == "nt", "Windows installer tests require Windows")
class WindowsInstallerTests(unittest.TestCase):
    """Exercise installer process-boundary behavior through PowerShell 5.1."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.powershell = _find_powershell()
        if cls.powershell is None:
            raise unittest.SkipTest("Windows PowerShell is unavailable")

    def _run_installer(self, fake_python_body: str) -> subprocess.CompletedProcess[str]:
        with tempfile.TemporaryDirectory() as temporary_directory:
            fake_python = Path(temporary_directory) / "fake-python.cmd"
            fake_python.write_text(fake_python_body, encoding="ascii")
            return subprocess.run(
                [
                    self.powershell,
                    "-NoProfile",
                    "-ExecutionPolicy",
                    "Bypass",
                    "-File",
                    str(INSTALLER_PATH),
                    "-Python",
                    str(fake_python),
                ],
                cwd=REPO_ROOT,
                capture_output=True,
                text=True,
                check=False,
            )

    def test_native_python_failure_propagates_to_installer_exit(self) -> None:
        result = self._run_installer(f"@echo off\r\nexit /b {FAILURE_EXIT_CODE}\r\n")

        self.assertNotEqual(0, result.returncode)
        self.assertNotIn("Done.", result.stdout)

    def test_python_older_than_minimum_is_rejected(self) -> None:
        result = self._run_installer(
            "@echo off\r\n"
            "echo 3.9.13\r\n"
            "exit /b 0\r\n"
        )

        self.assertNotEqual(0, result.returncode)
        self.assertIn("3.10", result.stdout + result.stderr)


class WindowsDependencyContractTests(unittest.TestCase):
    """Protect the repository-owned dependency and launcher contracts."""

    def test_requirements_are_complete_and_exclude_lark(self) -> None:
        requirements = {
            line.strip()
            for line in REQUIREMENTS_PATH.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }

        self.assertEqual(EXPECTED_REQUIREMENTS, requirements)
        self.assertFalse(any(line.lower().startswith("lark") for line in requirements))

    def test_legacy_installer_delegates_to_root_installer(self) -> None:
        content = (REPO_ROOT / "tools/can_nt/install_deps.bat").read_text(
            encoding="utf-8"
        )

        self.assertIn("install_windows.cmd", content)
        self.assertNotIn("pip install", content)

    def test_launchers_consider_repository_virtual_environment(self) -> None:
        powershell_launcher = (REPO_ROOT / "tools/can_nt/run_can_nt.ps1").read_text(
            encoding="utf-8"
        )
        batch_launcher = (REPO_ROOT / "tools/can_nt/run_can_nt.cmd").read_text(
            encoding="utf-8"
        )
        document_launcher = (REPO_ROOT / "tools/md_to_docx/md_to_docx.ps1").read_text(
            encoding="utf-8"
        )

        self.assertIn(".venv", powershell_launcher)
        self.assertIn(".venv", batch_launcher)
        self.assertIn(".venv", document_launcher)

    def test_regenerator_does_not_execute_powershell_with_python(self) -> None:
        content = (REPO_ROOT / "tools/can_nt/regen_cli_parser.ps1").read_text(
            encoding="utf-8"
        )

        self.assertNotIn("& $Python .\\install_windows.ps1", content)

    def test_ebnf_generator_runs_without_site_packages(self) -> None:
        source_directory = REPO_ROOT / "tools/can_nt"
        with tempfile.TemporaryDirectory() as temporary_directory:
            target_directory = Path(temporary_directory)
            for name in GENERATOR_SOURCE_NAMES:
                shutil.copy2(source_directory / name, target_directory / name)

            result = subprocess.run(
                [sys.executable, "-S", str(target_directory / GENERATOR_SOURCE_NAMES[0])],
                cwd=target_directory,
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stdout + result.stderr)
            self.assertTrue((target_directory / "bridge_cli_grammar_gen.py").is_file())
            self.assertTrue((target_directory / "bridge_cli_constants_gen.py").is_file())


if __name__ == "__main__":
    unittest.main()
