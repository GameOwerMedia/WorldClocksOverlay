import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

import app

ROOT = Path(__file__).resolve().parents[1]
PYINSTALLER_LINE = (
    'python -m PyInstaller --noconfirm --onefile --windowed --name WorldClockOverlay '
    '--add-data "config.json;." --collect-all tzdata app.py'
)


def _bat(name: str) -> str:
    return (ROOT / name).read_text(encoding="utf-8")


def test_batch_scripts_start_in_their_own_directory_and_share_the_build_command():
    for name in ("install.bat", "build.bat", "run_dev.bat", "uninstall.bat"):
        assert 'cd /d "%~dp0"' in _bat(name)

    install_lines = [line.strip() for line in _bat("install.bat").splitlines() if "PyInstaller" in line]
    build_lines = [line.strip() for line in _bat("build.bat").splitlines() if "PyInstaller" in line]
    assert install_lines == [PYINSTALLER_LINE]
    assert build_lines == [PYINSTALLER_LINE]
    assert 'pip install "pyinstaller>=6.3"' in _bat("install.bat")
    assert 'pip install "pyinstaller>=6.3"' in _bat("build.bat")
    for name in ("install.bat", "build.bat"):
        text = _bat(name)
        assert 'if not exist "dist\\config.json"' in text
        assert "copy /Y config.json dist\\config.json" not in text


def test_uninstall_removes_the_same_run_value_the_app_writes():
    text = _bat("uninstall.bat")
    assert "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run" in text
    assert app.AUTOSTART_RUN_KEY == r"Software\Microsoft\Windows\CurrentVersion\Run"
    assert f'/v "{app.AUTOSTART_RUN_VALUE}"' in text
    assert "reg delete" in text


def test_readme_relative_paths_exist():
    text = (ROOT / "README.md").read_text(encoding="utf-8")
    targets = re.findall(r'\]\(([^)]+)\)', text)
    targets += re.findall(r'(?:src|href)="([^"]+)"', text)
    for target in targets:
        if target.startswith(("http://", "https://", "mailto:", "#")):
            continue
        assert (ROOT / target).exists(), target


def test_pyinstaller_collects_tzdata_for_a_machine_without_system_zoneinfo(tmp_path):
    pytest.importorskip("PyInstaller")
    script = tmp_path / "tiny_zone.py"
    script.write_text(
        "from zoneinfo import ZoneInfo\nprint(ZoneInfo('America/New_York').key)\n",
        encoding="utf-8",
    )
    build = subprocess.run(
        [
            sys.executable,
            "-m",
            "PyInstaller",
            "--noconfirm",
            "--onefile",
            "--name",
            "tiny_zone",
            "--collect-all",
            "tzdata",
            str(script),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert build.returncode == 0, build.stderr[-2000:]
    binary = tmp_path / "dist" / "tiny_zone"
    from PyInstaller.archive.readers import CArchiveReader

    names = CArchiveReader(str(binary)).toc
    assert any(name.replace("\\", "/").endswith("tzdata/zoneinfo/America/New_York") for name in names)
    empty = tmp_path / "empty-tz"
    empty.mkdir()
    env = os.environ.copy()
    env["PYTHONTZPATH"] = str(empty)
    run = subprocess.run([str(binary)], capture_output=True, text=True, env=env, check=False)
    assert run.returncode == 0, run.stderr
    assert "America/New_York" in run.stdout
