import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import app


def test_format_clock_time_is_locale_independent():
    afternoon = datetime(2026, 1, 15, 13, 5, 9)
    midnight = datetime(2026, 1, 15, 0, 0, 0)
    noon = datetime(2026, 1, 15, 12, 0, 0)
    display_12 = {"use_24h": False, "show_seconds": False}
    display_12_seconds = {"use_24h": False, "show_seconds": True}
    display_24 = {"use_24h": True, "show_seconds": False}

    assert app.format_clock_time(afternoon, display_24) == "13:05"
    assert app.format_clock_time(afternoon, display_12) == "1:05 PM"
    assert app.format_clock_time(afternoon, display_12_seconds) == "1:05:09 PM"
    assert app.format_clock_time(midnight, display_12) == "12:00 AM"
    assert app.format_clock_time(noon, display_12) == "12:00 PM"
    assert app.sample_time_text(display_12) == "11:59 PM"
    assert app.sample_time_text({"use_24h": True, "show_seconds": True}) == "23:59:59"


def test_city_time_zones_match_known_offsets():
    cities = json.loads(Path("config.json").read_text(encoding="utf-8"))["cities"]
    assert len(cities) == 105
    zones = {city["timezone"] for city in cities}
    assert "America/New_York" in zones
    assert "Asia/Tokyo" in zones
    assert "Europe/Warsaw" in zones

    winter = datetime(2026, 1, 15, 16, 0, tzinfo=ZoneInfo("UTC"))
    summer = datetime(2026, 6, 15, 16, 0, tzinfo=ZoneInfo("UTC"))
    winter_ny = winter.astimezone(ZoneInfo("America/New_York"))
    summer_ny = summer.astimezone(ZoneInfo("America/New_York"))
    tokyo = winter.astimezone(ZoneInfo("Asia/Tokyo"))
    display = {"use_24h": True, "show_seconds": False}

    assert app.format_clock_time(winter_ny, display) == "11:00"
    assert app.format_clock_time(summer_ny, display) == "12:00"
    assert app.format_clock_time(tokyo, display) == "01:00"
    assert app.format_clock_time(summer_ny, {"use_24h": False, "show_seconds": False}) == "12:00 PM"
    for city in cities:
        ZoneInfo(city["timezone"])


def test_city_search_matches_label_or_timezone():
    tokyo = {"label": "Tokyo", "timezone": "Asia/Tokyo"}
    beijing = {"label": "Beijing", "timezone": "Asia/Shanghai"}
    shanghai = {"label": "Shanghai", "timezone": "Asia/Shanghai"}
    new_york = {"label": "New York", "timezone": "America/New_York"}

    assert app.city_matches_query(tokyo, "")
    assert app.city_matches_query(tokyo, "  ")
    assert app.city_matches_query(new_york, "new y")
    assert app.city_matches_query(new_york, "AMERICA/new")
    assert app.city_matches_query(beijing, "shanghai")
    assert app.city_matches_query(shanghai, "Shanghai")
    assert not app.city_matches_query(tokyo, "shanghai")


def test_scale_math_clamps_and_grows():
    assert app.next_scale(1.0, 0.2) == 1.2
    assert app.next_scale(2.0, 0.2) == 2.0
    assert app.next_scale(0.6, -0.2) == 0.6
    assert app.scaled_dimension(380, 1.0, 1.2, 100) == 456
    assert app.scaled_dimension(40, 1.0, 0.6, 50) == 50


def test_choose_default_city_prefers_local_then_fallbacks(monkeypatch):
    cities = [
        {"label": "London", "timezone": "Europe/London"},
        {"label": "Tokyo", "timezone": "Asia/Tokyo"},
    ]
    monkeypatch.setattr(app, "local_timezone_key", lambda: "Asia/Tokyo")
    assert app.choose_default_city(cities)["label"] == "Tokyo"
    monkeypatch.setattr(app, "local_timezone_key", lambda: "Pacific/Auckland")
    assert app.choose_default_city(cities)["label"] == "London"
    assert app.choose_default_city([]) is None


def test_normalize_enables_system_zone_only_when_unconfigured(monkeypatch):
    monkeypatch.setattr(app, "local_timezone_key", lambda: "Europe/Paris")
    fresh = app.normalize_config(
        {
            "cities": [
                {"label": "Paris", "timezone": "Europe/Paris"},
                {"label": "Tokyo", "timezone": "Asia/Tokyo"},
            ]
        }
    )
    by_label = {city["label"]: city for city in fresh["cities"]}
    assert by_label["Paris"]["placement"] == "line"
    assert by_label["Paris"]["enabled"] is True
    assert by_label["Tokyo"]["placement"] == "off"

    explicit_off = app.normalize_config(
        {"cities": [{"label": "Paris", "timezone": "Europe/Paris", "placement": "off", "enabled": False}]}
    )
    assert explicit_off["cities"][0]["placement"] == "off"
    assert explicit_off["cities"][0]["enabled"] is False

    invalid = app.normalize_config(
        {
            "cities": [
                {"label": "A", "timezone": "UTC", "placement": "nope", "enabled": True},
                {"label": "B", "timezone": "UTC", "placement": "bogus", "enabled": False},
            ]
        }
    )
    assert invalid["cities"][0]["placement"] == "line"
    assert invalid["cities"][1]["placement"] == "off"


def test_settings_round_trip_and_failed_save_keeps_the_previous_file(tmp_path, monkeypatch):
    path = tmp_path / "config.json"
    original = {"window": {"opacity": 0.5}, "display": {"theme": "black", "show_seconds": False}, "cities": []}
    path.write_text(json.dumps(original) + "\n", encoding="utf-8")
    monkeypatch.setattr(app, "config_path", lambda: str(path))

    cfg = app.normalize_config(app.load_config())
    cfg["display"]["theme"] = "white"
    cfg["display"]["show_seconds"] = True
    cfg["display"]["use_24h"] = False
    cfg["window"]["opacity"] = 0.4
    app.save_config_immediate(cfg)

    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded["display"]["theme"] == "white"
    assert loaded["display"]["show_seconds"] is True
    assert loaded["display"]["use_24h"] is False
    assert loaded["window"]["opacity"] == 0.4
    assert path.read_text(encoding="utf-8").endswith("\n")

    def fail_dump(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr(app.json, "dump", fail_dump)
    app.save_config_immediate({"cities": ["replaced"]})
    assert json.loads(path.read_text(encoding="utf-8"))["display"]["theme"] == "white"


def test_debounced_save_keeps_the_latest_config(qapp, tmp_path, monkeypatch):
    from PySide6.QtTest import QTest

    path = tmp_path / "config.json"
    path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(app, "config_path", lambda: str(path))
    cfg = {"display": {"theme": "black"}}
    app.save_config(cfg)
    cfg["display"]["theme"] = "white"
    app.save_config(cfg)
    assert path.read_text(encoding="utf-8") == "{}\n"
    QTest.qWait(app.SAVE_DEBOUNCE_MS + 200)
    assert json.loads(path.read_text(encoding="utf-8"))["display"]["theme"] == "white"


def test_autostart_command_for_executable_and_source(tmp_path):
    exe = r"C:\Program Files\WorldClockOverlay\WorldClockOverlay.exe"
    frozen = app.autostart_launch_command(frozen=True, executable=exe, script_path=r"C:\ignored\app.py")
    assert frozen == '"C:\\Program Files\\WorldClockOverlay\\WorldClockOverlay.exe"'

    scripts = tmp_path / "Scripts"
    scripts.mkdir()
    python_exe = scripts / "python.exe"
    pythonw_exe = scripts / "pythonw.exe"
    python_exe.write_text("", encoding="utf-8")
    pythonw_exe.write_text("", encoding="utf-8")
    script = tmp_path / "app.py"
    script.write_text("print('ok')\n", encoding="utf-8")
    source = app.autostart_launch_command(frozen=False, executable=str(python_exe), script_path=str(script))
    assert source == f'"{pythonw_exe}" "{script}"'

    bare = tmp_path / "python.exe"
    bare.write_text("", encoding="utf-8")
    fallback = app.autostart_launch_command(frozen=False, executable=str(bare), script_path=str(script))
    assert fallback == f'"{bare}" "{script}"'


def test_default_autostart_matches_the_platform():
    controller = app.default_autostart_controller()
    if sys.platform == "win32":
        assert isinstance(controller.store, app.WinregAutostartStore)
        assert controller.supported is True
    else:
        assert controller.supported is False
        assert "Windows" in controller.tooltip()


def test_autostart_controller_toggles_the_run_value():
    store = app.MemoryAutostartStore()
    command = r'"D:\dist\WorldClockOverlay.exe"'
    controller = app.AutostartController(store, command, supported=True)
    assert controller.is_enabled() is False
    controller.set_enabled(True)
    assert store.read() == command
    assert controller.is_enabled() is True
    assert controller.tooltip() == "Launch this program when you sign in to Windows."

    store.value = r'"C:\source\pythonw.exe" "C:\source\app.py"'
    assert controller.is_enabled() is True
    assert "pythonw.exe" in controller.tooltip()
    controller.set_enabled(False)
    assert store.read() is None

    unsupported = app.AutostartController(app.UnsupportedAutostartStore(), command, supported=False)
    assert unsupported.is_enabled() is False
    try:
        unsupported.set_enabled(True)
    except OSError as exc:
        assert "Windows" in str(exc)
    else:
        raise AssertionError("unsupported autostart should fail")


def test_winreg_store_uses_the_64bit_hkcu_run_key(monkeypatch):
    class FakeRegistry:
        def __init__(self):
            self.values = {}
            self.access_log = []
            self.HKEY_CURRENT_USER = "HKCU"
            self.KEY_READ = 0x20019
            self.KEY_SET_VALUE = 0x0002
            self.KEY_WOW64_64KEY = 0x0100
            self.REG_SZ = 1

        def OpenKey(self, root, path, reserved=0, access=0):
            self.access_log.append(("open", root, path, access))
            return self

        def CreateKeyEx(self, root, path, reserved=0, access=0):
            self.access_log.append(("create", root, path, access))
            return self

        def QueryValueEx(self, _key, name):
            if name not in self.values:
                raise FileNotFoundError(name)
            return self.values[name], self.REG_SZ

        def SetValueEx(self, _key, name, _reserved, typ, value):
            assert typ == self.REG_SZ
            self.values[name] = value

        def DeleteValue(self, _key, name):
            self.values.pop(name)

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    fake = FakeRegistry()
    monkeypatch.setitem(sys.modules, "winreg", fake)
    store = app.WinregAutostartStore()
    assert store.read() is None
    store.write(r'"C:\dist\WorldClockOverlay.exe"')
    assert store.read() == r'"C:\dist\WorldClockOverlay.exe"'
    store.delete()
    assert store.read() is None

    assert all(path == app.AUTOSTART_RUN_KEY for _op, _root, path, _access in fake.access_log)
    assert all(access & fake.KEY_WOW64_64KEY for _op, _root, _path, access in fake.access_log)
    assert app.AUTOSTART_RUN_VALUE not in fake.values


def test_frozen_config_is_copied_once_beside_the_executable(tmp_path, monkeypatch):
    exe_dir = tmp_path / "dist"
    bundle_dir = tmp_path / "bundle"
    exe_dir.mkdir()
    bundle_dir.mkdir()
    (bundle_dir / "config.json").write_text('{"source": "bundle"}\n', encoding="utf-8")
    monkeypatch.setattr(app.sys, "frozen", True, raising=False)
    monkeypatch.setattr(app.sys, "executable", str(exe_dir / "WorldClockOverlay.exe"))
    monkeypatch.setattr(app.sys, "_MEIPASS", str(bundle_dir), raising=False)

    app.ensure_config_next_to_exe()
    target = exe_dir / "config.json"
    assert target.read_text(encoding="utf-8") == '{"source": "bundle"}\n'
    target.write_text('{"source": "user"}\n', encoding="utf-8")
    app.ensure_config_next_to_exe()
    assert target.read_text(encoding="utf-8") == '{"source": "user"}\n'
