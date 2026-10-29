import json
import uuid
from pathlib import Path

from PySide6.QtCore import QEvent, QPointF, Qt
from PySide6.QtGui import QMouseEvent

import app


def _display():
    return {
        "show_seconds": False,
        "use_24h": True,
        "font_size_city": 11,
        "font_size_time": 20,
        "theme": "black",
    }


def _window(**overrides):
    data = {
        "x": None,
        "y": None,
        "width": 380,
        "height": 44,
        "opacity": 0.82,
        "always_on_top": True,
        "snap_bottom_right": True,
        "scale": 1.0,
    }
    data.update(overrides)
    return data


def _city(label, timezone, placement):
    return {
        "label": label,
        "timezone": timezone,
        "placement": placement,
        "enabled": placement != "off",
    }


def _write_config(tmp_path, monkeypatch, cfg):
    path = tmp_path / "config.json"
    path.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setattr(app, "config_path", lambda: str(path))
    return path


def _manager(qapp, tmp_path, monkeypatch, cities, window=None, autostart=None):
    cfg = app.normalize_config({"window": window or _window(), "display": _display(), "cities": cities})
    _write_config(tmp_path, monkeypatch, cfg)
    return app.ClockManager(qapp, app.normalize_config(app.load_config()), autostart=autostart)


def _close_manager(qapp, manager):
    manager.hide_all()
    manager.tray.hide()
    if manager.line_window is not None:
        manager.line_window.deleteLater()
        manager.line_window = None
    for window in list(manager.detached_windows.values()):
        window.deleteLater()
    manager.detached_windows.clear()
    qapp.processEvents()


def _mouse(kind, local_x, local_y, global_x, global_y):
    local = QPointF(local_x, local_y)
    remote = QPointF(global_x, global_y)
    return QMouseEvent(kind, local, remote, remote, Qt.LeftButton, Qt.LeftButton, Qt.NoModifier)


def test_startup_keeps_snap_and_places_the_line_in_the_corner(qapp, tmp_path, monkeypatch):
    manager = _manager(qapp, tmp_path, monkeypatch, [_city("Tokyo", "Asia/Tokyo", "line")])
    try:
        window = manager.line_window
        assert window is not None
        assert manager.cfg["window"]["snap_bottom_right"] is True
        geo = window.current_screen_geometry()
        assert abs(window.x() - (geo.right() - window.width() - 14)) <= 2
        assert abs(window.y() - (geo.bottom() - window.height() - 14)) <= 2
        assert window.cards[0].current_time_text not in {"--:--", "TZ ERR", "ERR"}
    finally:
        _close_manager(qapp, manager)


def test_saved_position_is_restored_and_offscreen_position_snaps_back(qapp, tmp_path, monkeypatch):
    restored = _manager(
        qapp,
        tmp_path,
        monkeypatch,
        [_city("London", "Europe/London", "line")],
        window=_window(x=30, y=40, snap_bottom_right=False),
    )
    try:
        assert restored.line_window.x() == 30
        assert restored.line_window.y() == 40
        assert restored.cfg["window"]["snap_bottom_right"] is False
    finally:
        _close_manager(qapp, restored)

    snapped = _manager(
        qapp,
        tmp_path,
        monkeypatch,
        [_city("London", "Europe/London", "window")],
        window=_window(),
    )
    try:
        detached = next(iter(snapped.detached_windows.values()))
        detached.window_cfg["x"] = 50000
        detached.window_cfg["y"] = 50000
        detached.window_cfg["snap_bottom_right"] = False
        detached.apply_initial_geometry()
        assert detached.window_cfg["snap_bottom_right"] is True
        geo = detached.current_screen_geometry()
        assert detached.x() < geo.right()
        assert detached.y() < geo.bottom()
        assert detached.x() > geo.left()
    finally:
        _close_manager(qapp, snapped)


def test_dragging_clears_snap_and_scroll_scales_the_window(qapp, tmp_path, monkeypatch):
    manager = _manager(qapp, tmp_path, monkeypatch, [_city("Tokyo", "Asia/Tokyo", "line"), _city("London", "Europe/London", "line")])
    try:
        window = manager.line_window
        origin_x = window.x()
        origin_y = window.y()
        window.mousePressEvent(_mouse(QEvent.MouseButtonPress, 4, 4, origin_x + 4, origin_y + 4))
        window.mouseMoveEvent(_mouse(QEvent.MouseMove, 40, 20, origin_x + 40, origin_y + 20))
        window.mouseReleaseEvent(_mouse(QEvent.MouseButtonRelease, 40, 20, origin_x + 40, origin_y + 20))
        assert manager.cfg["window"]["snap_bottom_right"] is False
        assert window.x() != origin_x or window.y() != origin_y
        assert manager.cfg["window"]["x"] == window.x()

        old_width = window.width()
        old_height = window.height()
        old_font = window.cards[0].time_label_widget.font().pointSize()
        window.scale_by(1.0)
        assert manager.cfg["window"]["scale"] == 2.0
        assert window.width() > old_width
        assert window.height() > old_height
        assert window.cards[0].time_label_widget.font().pointSize() > old_font
        window.scale_by(1.0)
        assert manager.cfg["window"]["scale"] == 2.0
    finally:
        _close_manager(qapp, manager)


def test_all_clocks_can_be_turned_off_and_the_choice_survives_reload(qapp, tmp_path, monkeypatch):
    cities = [_city("Tokyo", "Asia/Tokyo", "line"), _city("Paris", "Europe/Paris", "window")]
    manager = _manager(qapp, tmp_path, monkeypatch, cities)
    try:
        mapping = {app.city_key(city): app.PLACEMENT_OFF for city in manager.cfg["cities"]}
        manager.apply_selected_cities(mapping)
        assert manager.line_window is None
        assert manager.detached_windows == {}
        assert all(city["placement"] == "off" for city in manager.cfg["cities"])
        app.save_config_immediate(manager.cfg)
        reloaded = app.normalize_config(app.load_config())
        assert all(city["enabled"] is False for city in reloaded["cities"])
    finally:
        _close_manager(qapp, manager)


def test_city_dialog_filters_the_real_city_list(qapp):
    cities = json.loads(Path("config.json").read_text(encoding="utf-8"))["cities"]
    dialog = app.CitySelectionDialog(cities)
    dialog.show()
    qapp.processEvents()
    try:
        dialog.filter_items("new york")
        qapp.processEvents()
        visible = [city["label"] for row, _combo, city in dialog.rows if row.isVisible()]
        assert visible == ["New York"]

        dialog.filter_items("shanghai")
        qapp.processEvents()
        visible = sorted(city["label"] for row, _combo, city in dialog.rows if row.isVisible())
        assert visible == ["Beijing", "Shanghai"]

        dialog.filter_items("")
        qapp.processEvents()
        assert sum(1 for row, _combo, _city in dialog.rows if row.isVisible()) == 105
    finally:
        dialog.close()


def test_invalid_time_zone_is_shown_on_the_card(qapp):
    card = app.TimeCard("Nowhere", "Not/AZone", _display(), 1.0, 0.82)
    card.resize(160, 80)
    card.refresh_time()
    assert card.current_time_text == "TZ ERR"
    card.deleteLater()
    qapp.processEvents()


def test_start_with_windows_tray_action_writes_and_clears_the_command(qapp, tmp_path, monkeypatch):
    store = app.MemoryAutostartStore()
    command = r'"D:\dist\WorldClockOverlay.exe"'
    controller = app.AutostartController(store, command, supported=True)
    manager = _manager(
        qapp,
        tmp_path,
        monkeypatch,
        [_city("Tokyo", "Asia/Tokyo", "line")],
        autostart=controller,
    )
    try:
        action = next(item for item in manager.tray.contextMenu().actions() if item.text() == app.AUTOSTART_ACTION_TEXT)
        assert action.isEnabled()
        assert action.isChecked() is False
        action.trigger()
        qapp.processEvents()
        assert store.read() == command
        assert action.isChecked() is True
        action.trigger()
        qapp.processEvents()
        assert store.read() is None
        assert action.isChecked() is False

        menu = manager.tray.contextMenu()
        assert any(item.text() == "Show all clocks" for item in menu.actions())
        assert any(item.text() == "Add or remove clocks..." for item in menu.actions())
    finally:
        _close_manager(qapp, manager)


def test_second_instance_is_rejected_and_a_fresh_name_can_be_claimed(qapp):
    name = f"WorldClockOverlay-test-{uuid.uuid4().hex}"
    first = app.claim_single_instance(name)
    try:
        assert first is not None
        assert app.claim_single_instance(name) is None
    finally:
        if first is not None:
            first.close()
        app.QLocalServer.removeServer(name)
    again = app.claim_single_instance(name)
    assert again is not None
    again.close()
    app.QLocalServer.removeServer(name)
    qapp.processEvents()
