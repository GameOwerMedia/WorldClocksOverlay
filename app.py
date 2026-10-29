import json
import os
import shutil
import sys
import tempfile
from collections.abc import Callable
from contextlib import contextmanager
from datetime import datetime
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from PySide6.QtCore import QEvent, QPoint, QRect, Qt, QTimer
from PySide6.QtGui import QAction, QFont, QFontMetrics, QGuiApplication
from PySide6.QtNetwork import QAbstractSocket, QLocalServer, QLocalSocket
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMenu,
    QMessageBox,
    QScrollArea,
    QSizeGrip,
    QSizePolicy,
    QStyle,
    QSystemTrayIcon,
    QVBoxLayout,
    QWidget,
)

APP_NAME = "World Clock Overlay"
CONFIG_FILE_NAME = "config.json"
MIN_CITY_FONT_SIZE = 5
MIN_TIME_FONT_SIZE = 7
DEFAULT_CITY_FONT_SIZE = 10
DEFAULT_TIME_FONT_SIZE = 17
DEFAULT_CITY_WIDTH = 118
DEFAULT_CITY_HEIGHT = 50
PLACEMENT_OFF = "off"
PLACEMENT_LINE = "line"
PLACEMENT_WINDOW = "window"
SAVE_DEBOUNCE_MS = 500
MIN_WINDOW_SCALE = 0.6
MAX_WINDOW_SCALE = 2.0
AUTOSTART_RUN_KEY = r"Software\Microsoft\Windows\CurrentVersion\Run"
AUTOSTART_RUN_VALUE = "WorldClockOverlay"
AUTOSTART_ACTION_TEXT = "Start with Windows"
SINGLE_INSTANCE_NAME = "WorldClockOverlay"
_KEY_WOW64_64KEY = 0x0100


def app_base_dir() -> str:
    if getattr(sys, "frozen", False):
        return os.path.dirname(sys.executable)
    return os.path.dirname(os.path.abspath(__file__))


def config_path() -> str:
    return os.path.join(app_base_dir(), CONFIG_FILE_NAME)


def ensure_config_next_to_exe() -> None:
    if not getattr(sys, "frozen", False):
        return
    exe_dir = os.path.dirname(sys.executable)
    cfg = os.path.join(exe_dir, CONFIG_FILE_NAME)
    if not os.path.exists(cfg):
        bundled = os.path.join(getattr(sys, "_MEIPASS", exe_dir), CONFIG_FILE_NAME)
        if os.path.exists(bundled):
            shutil.copy2(bundled, cfg)


def load_config() -> dict:
    path = config_path()
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing config file: {path}")
    with open(path, "r", encoding="utf-8") as file:
        return json.load(file)


_save_timer: QTimer | None = None
_save_pending_cfg: dict | None = None


def _flush_save() -> None:
    global _save_pending_cfg
    if _save_pending_cfg is None:
        return
    cfg = _save_pending_cfg
    _save_pending_cfg = None
    path = config_path()
    directory = os.path.dirname(os.path.abspath(path)) or "."
    tmp_path = None
    try:
        fd, tmp_path = tempfile.mkstemp(prefix=".config-", suffix=".tmp", dir=directory)
        with os.fdopen(fd, "w", encoding="utf-8") as file:
            json.dump(cfg, file, indent=2, ensure_ascii=False)
            file.write("\n")
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, path)
        tmp_path = None
    except OSError as exc:
        print(f"Failed to save {path}: {exc}", file=sys.stderr)
        if tmp_path is not None:
            try:
                os.remove(tmp_path)
            except OSError:
                pass


def save_config(cfg: dict) -> None:
    global _save_timer, _save_pending_cfg
    _save_pending_cfg = cfg
    if _save_timer is None:
        _save_timer = QTimer()
        _save_timer.setSingleShot(True)
        _save_timer.timeout.connect(_flush_save)
    if _save_timer.isActive():
        _save_timer.stop()
    _save_timer.start(SAVE_DEBOUNCE_MS)


def save_config_immediate(cfg: dict) -> None:
    global _save_pending_cfg
    _save_pending_cfg = cfg
    _flush_save()


def config_opacity(cfg: dict) -> float:
    try:
        return max(0.2, min(1.0, float(cfg.get("window", {}).get("opacity", 0.82))))
    except (TypeError, ValueError):
        return 0.82


def alpha(base_alpha: int, opacity: float) -> int:
    if base_alpha <= 0:
        return 0
    return max(1, min(255, round(base_alpha * opacity)))


def root_frame_stylesheet(theme_name: str, opacity: float) -> str:
    if theme_name == "white":
        return f"""
            QFrame#rootFrame {{
                background-color: rgba(255, 255, 255, {alpha(105, opacity)});
                border: 1px solid rgba(0, 0, 0, {alpha(35, opacity)});
                border-radius: 16px;
            }}
        """
    return f"""
        QFrame#rootFrame {{
            background-color: rgba(20, 20, 20, {alpha(55, opacity)});
            border: 1px solid rgba(255, 255, 255, {alpha(28, opacity)});
            border-radius: 16px;
        }}
    """


def rect_is_visible_on_any_screen(x: int, y: int, width: int, height: int) -> bool:
    rect = QRect(x, y, max(1, width), max(1, height))
    for screen in QGuiApplication.screens():
        if rect.intersects(screen.availableGeometry()):
            return True
    return False


def city_key(city: dict) -> str:
    return f"{city.get('label', '')}|{city.get('timezone', '')}"


def format_clock_time(now: datetime, display_cfg: dict) -> str:
    """Format a clock time with locale-independent AM/PM.

    ``strftime("%p")`` follows the Windows regional format. Locales without
    AM/PM markers, including Polish, would otherwise show a 12-hour clock
    with a blank suffix.
    """
    show_seconds = bool(display_cfg.get("show_seconds", False))
    if display_cfg.get("use_24h", True):
        return now.strftime("%H:%M:%S" if show_seconds else "%H:%M")
    hour = now.hour % 12 or 12
    suffix = "AM" if now.hour < 12 else "PM"
    if show_seconds:
        return f"{hour}:{now.minute:02d}:{now.second:02d} {suffix}"
    return f"{hour}:{now.minute:02d} {suffix}"


def sample_time_text(display_cfg: dict) -> str:
    use_24h = display_cfg.get("use_24h", True)
    show_seconds = display_cfg.get("show_seconds", False)
    if use_24h:
        return "23:59:59" if show_seconds else "23:59"
    return "11:59:59 PM" if show_seconds else "11:59 PM"


def city_matches_query(city: dict, query: str) -> bool:
    text = query.strip().lower()
    if not text:
        return True
    haystack = f"{city.get('label', '')} {city.get('timezone', '')}".lower()
    return text in haystack


def next_scale(current: float, delta_steps: float) -> float:
    return round(max(MIN_WINDOW_SCALE, min(MAX_WINDOW_SCALE, float(current) + delta_steps)), 2)


def scaled_dimension(current: int, old_scale: float, new_scale: float, minimum: int) -> int:
    if old_scale <= 0:
        return max(minimum, current)
    grown = round(current * (float(new_scale) / float(old_scale)))
    return max(minimum, grown)


def _normalize_launch_path(path: str) -> str:
    if os.path.isabs(path):
        return os.path.abspath(path) if sys.platform == "win32" else path
    if len(path) >= 3 and path[1] == ":" and path[2] in "\\/":
        return path
    if path.startswith("\\\\"):
        return path
    return os.path.abspath(path)


def _quote_windows_arg(value: str) -> str:
    return '"' + value.replace('"', '\\"') + '"'


def _prefer_pythonw(executable: str) -> str:
    executable = _normalize_launch_path(executable)
    name = os.path.basename(executable).lower()
    if name.startswith("python") and name.endswith(".exe") and not name.startswith("pythonw"):
        candidate = os.path.join(os.path.dirname(executable), "pythonw.exe")
        if os.path.isfile(candidate):
            return candidate
    return executable


def autostart_launch_command(*, frozen: bool, executable: str, script_path: str) -> str:
    """Command stored in the HKCU Run key for this process.

    The built executable is registered by its own path. A source run prefers
    ``pythonw.exe`` next to the interpreter so Windows does not open a console.
    ``uninstall.bat`` deletes the same Run value regardless of which command
    was stored.
    """
    if frozen:
        return _quote_windows_arg(_normalize_launch_path(executable))
    interpreter = _prefer_pythonw(executable)
    script = _normalize_launch_path(script_path)
    return f"{_quote_windows_arg(interpreter)} {_quote_windows_arg(script)}"


def current_autostart_command() -> str:
    return autostart_launch_command(
        frozen=bool(getattr(sys, "frozen", False)),
        executable=sys.executable,
        script_path=os.path.abspath(__file__),
    )


class MemoryAutostartStore:
    def __init__(self, value: str | None = None):
        self.value = value

    def read(self) -> str | None:
        return self.value

    def write(self, command: str) -> None:
        self.value = command

    def delete(self) -> None:
        self.value = None


class UnsupportedAutostartStore:
    def read(self) -> str | None:
        return None

    def write(self, command: str) -> None:
        raise OSError("Start with Windows is only available on Windows.")

    def delete(self) -> None:
        raise OSError("Start with Windows is only available on Windows.")


class WinregAutostartStore:
    """HKCU Run value named WorldClockOverlay, in the 64-bit registry view.

    A 32-bit Python would otherwise be redirected to Wow6432Node, which
    Windows does not read at sign-in. ``uninstall.bat`` deletes this value
    with ``reg delete``.
    """

    def _access(self, write: bool):
        import winreg

        base = winreg.KEY_SET_VALUE if write else winreg.KEY_READ
        wow64 = getattr(winreg, "KEY_WOW64_64KEY", _KEY_WOW64_64KEY)
        return base | wow64

    def read(self) -> str | None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_RUN_KEY, 0, self._access(False)) as key:
                value, _regtype = winreg.QueryValueEx(key, AUTOSTART_RUN_VALUE)
        except FileNotFoundError:
            return None
        except OSError:
            return None
        text = str(value).strip() if value is not None else ""
        return text or None

    def write(self, command: str) -> None:
        import winreg

        with winreg.CreateKeyEx(winreg.HKEY_CURRENT_USER, AUTOSTART_RUN_KEY, 0, self._access(True)) as key:
            winreg.SetValueEx(key, AUTOSTART_RUN_VALUE, 0, winreg.REG_SZ, command)

    def delete(self) -> None:
        import winreg

        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, AUTOSTART_RUN_KEY, 0, self._access(True)) as key:
                winreg.DeleteValue(key, AUTOSTART_RUN_VALUE)
        except FileNotFoundError:
            return


class AutostartController:
    def __init__(self, store, command: str, supported: bool = True):
        self.store = store
        self.command = command
        self.supported = supported

    def is_enabled(self) -> bool:
        if not self.supported:
            return False
        return bool(self.store.read())

    def set_enabled(self, enabled: bool) -> None:
        if enabled:
            self.store.write(self.command)
        else:
            self.store.delete()

    def tooltip(self) -> str:
        if not self.supported:
            return "Start with Windows is only available on Windows."
        current = self.store.read()
        if current and current != self.command:
            return f"Currently registered as: {current}"
        return "Launch this program when you sign in to Windows."


def default_autostart_controller() -> AutostartController:
    command = current_autostart_command()
    if sys.platform == "win32":
        return AutostartController(WinregAutostartStore(), command, supported=True)
    return AutostartController(UnsupportedAutostartStore(), command, supported=False)


def claim_single_instance(name: str = SINGLE_INSTANCE_NAME) -> QLocalServer | None:
    """Return a listening server, or None when another instance is running.

    The caller must keep the returned server alive. A crashed process releases
    the name; ``removeServer`` clears a stale socket before listening.
    """
    probe = QLocalSocket()
    probe.connectToServer(name)
    if probe.waitForConnected(200):
        probe.disconnectFromServer()
        return None
    QLocalServer.removeServer(name)
    server = QLocalServer()
    if server.listen(name):
        return server
    if server.serverError() == QAbstractSocket.SocketError.AddressInUseError:
        return None
    return server


def show_message(icon: QMessageBox.Icon, title: str, text: str) -> None:
    box = QMessageBox()
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setWindowFlag(Qt.WindowStaysOnTopHint, True)
    box.exec()


def place_window_initially(window: QWidget, width: int, height: int, saved_x, saved_y, snap: bool, snap_to_corner: Callable[[], None]) -> None:
    window._applying_geometry = True
    try:
        window.resize(width, height)
        visible = (
            saved_x is not None
            and saved_y is not None
            and rect_is_visible_on_any_screen(int(saved_x), int(saved_y), width, height)
        )
        if visible:
            window.move(int(saved_x), int(saved_y))
        if snap or not visible:
            snap_to_corner()
        window.show()
    finally:
        window._applying_geometry = False
        window._geometry_ready = True


def local_timezone_key() -> str | None:
    return getattr(datetime.now().astimezone().tzinfo, "key", None)


def choose_default_city(cities: list[dict]) -> dict | None:
    if not cities:
        return None

    local_tz = local_timezone_key()
    if local_tz:
        for city in cities:
            if city.get("timezone") == local_tz:
                return city

    for fallback_tz in ("Europe/Warsaw", "Europe/London", "America/New_York", "Asia/Tokyo"):
        for city in cities:
            if city.get("timezone") == fallback_tz:
                return city

    return cities[0]


def ensure_city_window(city: dict, index: int) -> dict:
    window_cfg = city.setdefault("window", {})
    window_cfg.setdefault("width", DEFAULT_CITY_WIDTH)
    window_cfg.setdefault("height", DEFAULT_CITY_HEIGHT)
    window_cfg.setdefault("scale", 1.0)
    window_cfg.setdefault("x", None)
    window_cfg.setdefault("y", None)
    window_cfg.setdefault("snap_bottom_right", True)
    window_cfg.setdefault("offset_index", index)
    return window_cfg


def normalize_config(cfg: dict) -> dict:
    window_cfg = cfg.setdefault("window", {})
    display_cfg = cfg.setdefault("display", {})
    cities = cfg.setdefault("cities", [])

    window_cfg.setdefault("opacity", 0.82)
    window_cfg.setdefault("always_on_top", True)
    window_cfg.setdefault("snap_bottom_right", True)
    window_cfg.setdefault("scale", 1.0)
    window_cfg.setdefault("width", 240)
    window_cfg.setdefault("height", 64)
    window_cfg.setdefault("x", None)
    window_cfg.setdefault("y", None)

    display_cfg.setdefault("show_seconds", False)
    display_cfg.setdefault("use_24h", True)
    display_cfg.setdefault("font_size_city", 11)
    display_cfg.setdefault("font_size_time", 20)
    display_cfg.setdefault("theme", "black")

    valid_placements = {PLACEMENT_OFF, PLACEMENT_LINE, PLACEMENT_WINDOW}
    configured = any(city.get("placement") in valid_placements for city in cities)

    for index, city in enumerate(cities):
        city.setdefault("label", "Clock")
        city.setdefault("timezone", "UTC")
        placement = city.get("placement")
        if placement not in valid_placements:
            placement = PLACEMENT_LINE if city.get("enabled", False) else PLACEMENT_OFF
        city["placement"] = placement
        city["enabled"] = placement != PLACEMENT_OFF
        ensure_city_window(city, index)

    # A config that already names placements, including all Off, is left alone.
    # Only a list with no placements yet gets the system time zone on the line.
    if not configured and not any(city.get("enabled", False) for city in cities):
        default_city = choose_default_city(cities)
        if default_city is not None:
            default_city["placement"] = PLACEMENT_LINE
            default_city["enabled"] = True

    return cfg


def measure_card_size(label: str, display_cfg: dict, scale: float) -> tuple[int, int]:
    city_font = QFont("Segoe UI", MIN_CITY_FONT_SIZE)
    city_font.setBold(True)
    time_font = QFont("Segoe UI", MIN_TIME_FONT_SIZE)
    time_font.setBold(True)

    city_metrics = QFontMetrics(city_font)
    time_metrics = QFontMetrics(time_font)
    city_width = city_metrics.horizontalAdvance(label.upper())
    time_width = time_metrics.horizontalAdvance(sample_time_text(display_cfg))
    width = max(city_width, time_width) + 16
    height = city_metrics.height() + time_metrics.height() + 10
    # Scale 1 keeps the compact default. Larger scales raise the floor so the
    # scrolled-up font is not immediately clipped by the old minimum.
    factor = max(1.0, float(scale))
    return round(width * factor), round(height * factor)


class CitySelectionDialog(QDialog):
    def __init__(
        self,
        cities: list[dict],
        on_apply: Callable[[dict[str, str]], None] | None = None,
        parent: QWidget | None = None,
    ):
        super().__init__(parent)
        self.on_apply = on_apply
        self.rows: list[tuple[QWidget, QComboBox, dict]] = []
        self.setWindowTitle("Manage clocks")
        self.setWindowFlag(Qt.WindowStaysOnTopHint, True)
        self.resize(520, 620)
        self.setModal(True)

        layout = QVBoxLayout(self)
        header = QLabel("Choose how each city should open: Off, Line window, or Separate window.")
        header.setWordWrap(True)
        layout.addWidget(header)

        self.summary_label = QLabel()
        layout.addWidget(self.summary_label)

        self.search_input = QLineEdit(self)
        self.search_input.setPlaceholderText("Search by city or timezone...")
        self.search_input.textChanged.connect(self.filter_items)
        layout.addWidget(self.search_input)

        self.scroll_area = QScrollArea(self)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        layout.addWidget(self.scroll_area)

        self.scroll_content = QWidget(self.scroll_area)
        self.scroll_layout = QVBoxLayout(self.scroll_content)
        self.scroll_layout.setContentsMargins(6, 6, 6, 6)
        self.scroll_layout.setSpacing(6)
        self.scroll_layout.setAlignment(Qt.AlignTop)

        for city in cities:
            row_widget = QWidget(self.scroll_content)
            row_layout = QHBoxLayout(row_widget)
            row_layout.setContentsMargins(4, 2, 4, 2)
            row_layout.setSpacing(10)

            label = QLabel(f'{city["label"]} ({city["timezone"]})', row_widget)
            label.setWordWrap(True)
            row_layout.addWidget(label, 1)

            combo = QComboBox(row_widget)
            combo.addItem("Off", PLACEMENT_OFF)
            combo.addItem("Line window", PLACEMENT_LINE)
            combo.addItem("Separate window", PLACEMENT_WINDOW)
            combo.setCurrentIndex(max(0, combo.findData(city.get("placement", PLACEMENT_OFF))))
            combo.currentIndexChanged.connect(self.update_summary)
            row_layout.addWidget(combo)

            self.scroll_layout.addWidget(row_widget)
            self.rows.append((row_widget, combo, city))

        self.scroll_area.setWidget(self.scroll_content)

        buttons = QDialogButtonBox(QDialogButtonBox.Close)
        apply_button = buttons.addButton("Apply", QDialogButtonBox.AcceptRole)
        apply_button.clicked.connect(self.apply_selection)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)
        self.update_summary()

    def filter_items(self, text: str) -> None:
        for row_widget, _combo, city in self.rows:
            row_widget.setVisible(city_matches_query(city, text))

    def selected_mapping(self) -> dict[str, str]:
        return {city_key(city): combo.currentData() for _row, combo, city in self.rows}

    def update_summary(self) -> None:
        placements = self.selected_mapping().values()
        line_count = sum(1 for value in placements if value == PLACEMENT_LINE)
        separate_count = sum(1 for value in placements if value == PLACEMENT_WINDOW)
        self.summary_label.setText(
            f"Active clocks: {line_count + separate_count} | Line window: {line_count} | Separate windows: {separate_count}"
        )

    def apply_selection(self) -> None:
        if self.on_apply is not None:
            self.on_apply(self.selected_mapping())
        self.update_summary()


class TimeCard(QFrame):
    def __init__(self, city_label: str, timezone_name: str, display_cfg: dict, scale: float, opacity: float):
        super().__init__()
        self.city_label = city_label.upper()
        self.timezone_name = timezone_name
        self.display_cfg = display_cfg
        self.scale = scale
        self.opacity = opacity
        self.current_time_text = "--:--"

        self.setObjectName("timeCard")
        self.layout_box = QVBoxLayout(self)
        self.layout_box.setContentsMargins(8, 5, 8, 5)
        self.layout_box.setSpacing(0)
        self.layout_box.setAlignment(Qt.AlignCenter)

        self.city_label_widget = QLabel(self.city_label)
        self.city_label_widget.setAlignment(Qt.AlignCenter)
        self.time_label_widget = QLabel(self.current_time_text)
        self.time_label_widget.setAlignment(Qt.AlignCenter)

        self.layout_box.addWidget(self.city_label_widget)
        self.layout_box.addWidget(self.time_label_widget)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.apply_theme(self.display_cfg.get("theme", "black"))
        self.update_fonts()

    def apply_theme(self, theme_name: str) -> None:
        if theme_name == "white":
            bg_alpha = alpha(155, self.opacity)
            border_alpha = alpha(35, self.opacity)
            text_alpha = alpha(230, self.opacity)
            self.setStyleSheet(
                f"""
                QFrame#timeCard {{
                    background-color: rgba(255, 255, 255, {bg_alpha});
                    border: 1px solid rgba(0, 0, 0, {border_alpha});
                    border-radius: 12px;
                }}
                QLabel {{
                    color: rgba(20, 20, 20, {text_alpha});
                    background: transparent;
                }}
                """
            )
            return

        bg_alpha = alpha(95, self.opacity)
        border_alpha = alpha(35, self.opacity)
        text_alpha = alpha(255, self.opacity)
        self.setStyleSheet(
            f"""
            QFrame#timeCard {{
                background-color: rgba(15, 15, 15, {bg_alpha});
                border: 1px solid rgba(255, 255, 255, {border_alpha});
                border-radius: 12px;
            }}
            QLabel {{
                color: rgba(255, 255, 255, {text_alpha});
                background: transparent;
            }}
            """
        )

    def _fit_font_size(self, text: str, target_height: int, target_width: int, base_size: int, min_size: int) -> int:
        size = max(min_size, base_size)
        while size > min_size:
            font = QFont("Segoe UI", size)
            font.setBold(True)
            metrics = QFontMetrics(font)
            if metrics.horizontalAdvance(text) <= target_width and metrics.height() <= target_height:
                return size
            size -= 1
        return min_size

    def update_fonts(self) -> None:
        horizontal_margin = max(3, min(8, self.width() // 16))
        vertical_margin = max(2, min(6, self.height() // 16))
        self.layout_box.setContentsMargins(horizontal_margin, vertical_margin, horizontal_margin, vertical_margin)

        content_width = max(36, self.width() - (horizontal_margin * 2))
        content_height = max(24, self.height() - (vertical_margin * 2))
        city_height = max(8, int(content_height * 0.32))
        time_height = max(12, int(content_height * 0.56))

        base_city = max(MIN_CITY_FONT_SIZE, int(self.display_cfg.get("font_size_city", DEFAULT_CITY_FONT_SIZE) * self.scale))
        base_time = max(MIN_TIME_FONT_SIZE, int(self.display_cfg.get("font_size_time", DEFAULT_TIME_FONT_SIZE) * self.scale))

        city_size = self._fit_font_size(self.city_label, city_height, content_width, base_city, MIN_CITY_FONT_SIZE)
        time_size = self._fit_font_size(sample_time_text(self.display_cfg), time_height, content_width, base_time, MIN_TIME_FONT_SIZE)

        city_font = QFont("Segoe UI", city_size)
        city_font.setBold(True)
        self.city_label_widget.setFont(city_font)

        time_font = QFont("Segoe UI", time_size)
        time_font.setBold(True)
        self.time_label_widget.setFont(time_font)

    def refresh_time(self) -> None:
        try:
            tz = ZoneInfo(self.timezone_name)
            now = datetime.now(tz)
            self.current_time_text = format_clock_time(now, self.display_cfg)
            self.time_label_widget.setText(self.current_time_text)
        except ZoneInfoNotFoundError:
            self.current_time_text = "TZ ERR"
            self.time_label_widget.setText(self.current_time_text)
        except (TypeError, ValueError, OSError, OverflowError):
            self.current_time_text = "ERR"
            self.time_label_widget.setText(self.current_time_text)

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        self.update_fonts()


class SingleClockWindow(QWidget):
    def __init__(self, manager: "ClockManager", city: dict):
        super().__init__()
        self.manager = manager
        self.city = city
        self.window_cfg = ensure_city_window(city, 0)
        self.drag_active = False
        self.drag_offset = QPoint()
        self._applying_geometry = False
        self._geometry_ready = False

        self.apply_window_flags()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(f"{APP_NAME} - {city['label']}")

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.root = QFrame(self)
        self.root.setObjectName("rootFrame")
        self.outer_layout.addWidget(self.root)

        self.root_layout = QVBoxLayout(self.root)
        self.root_layout.setContentsMargins(8, 8, 8, 8)
        self.root_layout.setSpacing(0)

        self.card = TimeCard(
            city["label"],
            city["timezone"],
            self.manager.cfg["display"],
            float(self.window_cfg.get("scale", 1.0)),
            config_opacity(self.manager.cfg),
        )
        self.root_layout.addWidget(self.card)

        self.size_grip = QSizeGrip(self.root)
        self.size_grip.setFixedSize(10, 10)
        self.size_grip.raise_()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.card.refresh_time)
        self.timer.start(1000)

        self.apply_theme()
        self.apply_initial_geometry()
        self.card.refresh_time()

    def apply_window_flags(self) -> None:
        flags = Qt.FramelessWindowHint | Qt.Window | Qt.WindowDoesNotAcceptFocus
        if self.manager.cfg["window"].get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _restore_overlay_visibility(self) -> None:
        if self.manager.restore_suspended:
            return
        if self.isVisible():
            self.show()
            self.raise_()

    def event(self, event) -> bool:
        if event.type() in {QEvent.WindowDeactivate, QEvent.ActivationChange}:
            QTimer.singleShot(0, self._restore_overlay_visibility)
            QTimer.singleShot(150, self._restore_overlay_visibility)
        return super().event(event)

    def apply_theme(self) -> None:
        theme_name = self.manager.cfg["display"].get("theme", "black")
        opacity = config_opacity(self.manager.cfg)
        self.root.setStyleSheet(root_frame_stylesheet(theme_name, opacity))
        self.card.display_cfg = self.manager.cfg["display"]
        self.card.opacity = opacity
        self.card.apply_theme(theme_name)
        self.card.update_fonts()

    def minimum_clock_size(self) -> tuple[int, int]:
        card_width, card_height = measure_card_size(self.city["label"], self.manager.cfg["display"], float(self.window_cfg.get("scale", 1.0)))
        return card_width + 12, card_height + 12

    def apply_initial_geometry(self) -> None:
        min_width, min_height = self.minimum_clock_size()
        width = max(min_width, int(self.window_cfg.get("width", DEFAULT_CITY_WIDTH)))
        height = max(min_height, int(self.window_cfg.get("height", DEFAULT_CITY_HEIGHT)))
        self.setMinimumSize(min_width, min_height)
        place_window_initially(
            self,
            width,
            height,
            self.window_cfg.get("x"),
            self.window_cfg.get("y"),
            bool(self.window_cfg.get("snap_bottom_right", True)),
            lambda: self.snap_bottom_right(save_state=False),
        )

    def current_screen_geometry(self) -> QRect:
        screen = QGuiApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1280, 720)

    def snap_bottom_right(self, save_state: bool = True) -> None:
        geo = self.current_screen_geometry()
        margin = 14
        offset_index = int(self.window_cfg.get("offset_index", 0))
        self.move(geo.right() - self.width() - margin - (offset_index * 28), geo.bottom() - self.height() - margin - (offset_index * 6))
        self.window_cfg["snap_bottom_right"] = True
        if save_state:
            self.save_window_state()

    def save_window_state(self) -> None:
        self.window_cfg["x"] = int(self.x())
        self.window_cfg["y"] = int(self.y())
        self.window_cfg["width"] = int(self.width())
        self.window_cfg["height"] = int(self.height())
        save_config(self.manager.cfg)

    def scale_by(self, delta_steps: float) -> None:
        current = float(self.window_cfg.get("scale", 1.0))
        updated = next_scale(current, delta_steps)
        if updated == current:
            return
        old_width = self.width()
        old_height = self.height()
        self.window_cfg["scale"] = updated
        self.card.scale = updated
        min_width, min_height = self.minimum_clock_size()
        self.setMinimumSize(min_width, min_height)
        self.resize(
            scaled_dimension(old_width, current, updated, min_width),
            scaled_dimension(old_height, current, updated, min_height),
        )
        self.card.update_fonts()
        self.save_window_state()

    def close_clock(self) -> None:
        self.manager.remove_clock(city_key(self.city))

    def closeEvent(self, event) -> None:
        event.ignore()
        self.close_clock()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.drag_active = True
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_active and event.buttons() & Qt.LeftButton:
            self.window_cfg["snap_bottom_right"] = False
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self.drag_active = False
        self.save_window_state()
        event.accept()

    def wheelEvent(self, event) -> None:
        self.scale_by(0.05 if event.angleDelta().y() > 0 else -0.05)
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        min_width, min_height = self.minimum_clock_size()
        self.setMinimumSize(min_width, min_height)
        self.size_grip.move(max(0, self.root.width() - self.size_grip.width() - 5), max(0, self.root.height() - self.size_grip.height() - 5))
        self.card.update_fonts()
        if self._applying_geometry or not self._geometry_ready:
            return
        self.save_window_state()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        self.manager.populate_common_menu(menu)

        act_snap = QAction("Snap to bottom-right", self)
        act_snap.triggered.connect(self.snap_bottom_right)
        act_save = QAction("Save position", self)
        act_save.triggered.connect(self.save_window_state)
        act_close = QAction("Close this clock", self)
        act_close.triggered.connect(self.close_clock)

        menu.addSeparator()
        menu.addAction(act_snap)
        menu.addAction(act_save)
        menu.addSeparator()
        menu.addAction(act_close)
        menu.addAction(self.manager.exit_action(self))
        with self.manager.suspend_overlay_restore():
            menu.exec(event.globalPos())


class LineClockWindow(QWidget):
    def __init__(self, manager: "ClockManager"):
        super().__init__()
        self.manager = manager
        self.drag_active = False
        self.drag_offset = QPoint()
        self.cards: list[TimeCard] = []
        self._applying_geometry = False
        self._geometry_ready = False

        self.apply_window_flags()
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle(f"{APP_NAME} - Line Window")

        self.outer_layout = QVBoxLayout(self)
        self.outer_layout.setContentsMargins(0, 0, 0, 0)
        self.root = QFrame(self)
        self.root.setObjectName("rootFrame")
        self.outer_layout.addWidget(self.root)

        self.root_layout = QVBoxLayout(self.root)
        self.root_layout.setContentsMargins(8, 8, 8, 8)
        self.root_layout.setSpacing(0)

        self.cards_host = QWidget(self.root)
        self.cards_layout = QHBoxLayout(self.cards_host)
        self.cards_layout.setContentsMargins(0, 0, 0, 0)
        self.cards_layout.setSpacing(8)
        self.root_layout.addWidget(self.cards_host)

        self.size_grip = QSizeGrip(self.root)
        self.size_grip.setFixedSize(10, 10)
        self.size_grip.raise_()

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh_times)
        self.timer.start(1000)

        self.rebuild_cards()
        self.apply_theme()
        self.apply_initial_geometry()
        self.refresh_times()

    def line_cities(self) -> list[dict]:
        return self.manager.line_cities()

    def apply_window_flags(self) -> None:
        flags = Qt.FramelessWindowHint | Qt.Window | Qt.WindowDoesNotAcceptFocus
        if self.manager.cfg["window"].get("always_on_top", True):
            flags |= Qt.WindowStaysOnTopHint
        self.setWindowFlags(flags)

    def _restore_overlay_visibility(self) -> None:
        if self.manager.restore_suspended:
            return
        if self.isVisible():
            self.show()
            self.raise_()

    def event(self, event) -> bool:
        if event.type() in {QEvent.WindowDeactivate, QEvent.ActivationChange}:
            QTimer.singleShot(0, self._restore_overlay_visibility)
            QTimer.singleShot(150, self._restore_overlay_visibility)
        return super().event(event)

    def apply_theme(self) -> None:
        theme_name = self.manager.cfg["display"].get("theme", "black")
        opacity = config_opacity(self.manager.cfg)
        self.root.setStyleSheet(root_frame_stylesheet(theme_name, opacity))
        for card in self.cards:
            card.display_cfg = self.manager.cfg["display"]
            card.opacity = opacity
            card.apply_theme(theme_name)
            card.update_fonts()

    def rebuild_cards(self) -> None:
        while self.cards_layout.count():
            item = self.cards_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                widget.deleteLater()
        self.cards = []

        scale = float(self.manager.cfg["window"].get("scale", 1.0))
        opacity = config_opacity(self.manager.cfg)
        for city in self.line_cities():
            card = TimeCard(city["label"], city["timezone"], self.manager.cfg["display"], scale, opacity)
            card.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.cards_layout.addWidget(card)
            self.cards.append(card)

    def minimum_line_size(self) -> tuple[int, int]:
        cities = self.line_cities()
        if not cities:
            return 120, 50
        scale = float(self.manager.cfg["window"].get("scale", 1.0))
        sizes = [measure_card_size(city["label"], self.manager.cfg["display"], scale) for city in cities]
        return (
            sum(width for width, _ in sizes) + max(0, (len(sizes) - 1) * self.cards_layout.spacing()) + 16,
            max(height for _, height in sizes) + 12,
        )

    def apply_initial_geometry(self) -> None:
        min_width, min_height = self.minimum_line_size()
        self.setMinimumSize(min_width, min_height)
        saved_width = int(self.manager.cfg["window"].get("width", min_width))
        saved_height = int(self.manager.cfg["window"].get("height", min_height))
        width = max(min_width, saved_width)
        height = max(min_height, saved_height)
        place_window_initially(
            self,
            width,
            height,
            self.manager.cfg["window"].get("x"),
            self.manager.cfg["window"].get("y"),
            bool(self.manager.cfg["window"].get("snap_bottom_right", True)),
            lambda: self.snap_bottom_right(save_state=False),
        )

    def current_screen_geometry(self) -> QRect:
        screen = QGuiApplication.screenAt(self.frameGeometry().center())
        if screen is None:
            screen = QGuiApplication.primaryScreen()
        return screen.availableGeometry() if screen else QRect(0, 0, 1280, 720)

    def snap_bottom_right(self, save_state: bool = True) -> None:
        geo = self.current_screen_geometry()
        margin = 14
        self.move(geo.right() - self.width() - margin, geo.bottom() - self.height() - margin)
        self.manager.cfg["window"]["snap_bottom_right"] = True
        if save_state:
            self.save_window_state()

    def save_window_state(self) -> None:
        self.manager.cfg["window"]["x"] = int(self.x())
        self.manager.cfg["window"]["y"] = int(self.y())
        self.manager.cfg["window"]["width"] = int(self.width())
        self.manager.cfg["window"]["height"] = int(self.height())
        save_config(self.manager.cfg)

    def refresh_times(self) -> None:
        for card in self.cards:
            card.refresh_time()

    def scale_by(self, delta_steps: float) -> None:
        current = float(self.manager.cfg["window"].get("scale", 1.0))
        updated = next_scale(current, delta_steps)
        if updated == current:
            return
        old_width = self.width()
        old_height = self.height()
        self.manager.cfg["window"]["scale"] = updated
        for card in self.cards:
            card.scale = updated
        min_width, min_height = self.minimum_line_size()
        self.setMinimumSize(min_width, min_height)
        self.resize(
            scaled_dimension(old_width, current, updated, min_width),
            scaled_dimension(old_height, current, updated, min_height),
        )
        for card in self.cards:
            card.update_fonts()
        self.save_window_state()

    def closeEvent(self, event) -> None:
        event.ignore()
        self.hide()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.LeftButton:
            self.drag_active = True
            self.drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event) -> None:
        if self.drag_active and event.buttons() & Qt.LeftButton:
            self.manager.cfg["window"]["snap_bottom_right"] = False
            self.move(event.globalPosition().toPoint() - self.drag_offset)
            event.accept()

    def mouseReleaseEvent(self, event) -> None:
        self.drag_active = False
        self.save_window_state()
        event.accept()

    def wheelEvent(self, event) -> None:
        self.scale_by(0.05 if event.angleDelta().y() > 0 else -0.05)
        event.accept()

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        min_width, min_height = self.minimum_line_size()
        self.setMinimumSize(min_width, min_height)
        self.size_grip.move(max(0, self.root.width() - self.size_grip.width() - 5), max(0, self.root.height() - self.size_grip.height() - 5))
        for card in self.cards:
            card.update_fonts()
        if self._applying_geometry or not self._geometry_ready:
            return
        self.save_window_state()

    def contextMenuEvent(self, event) -> None:
        menu = QMenu(self)
        self.manager.populate_common_menu(menu)

        act_snap = QAction("Snap to bottom-right", self)
        act_snap.triggered.connect(self.snap_bottom_right)
        act_save = QAction("Save position", self)
        act_save.triggered.connect(self.save_window_state)
        act_hide = QAction("Hide line window", self)
        act_hide.triggered.connect(self.hide)

        menu.addSeparator()
        menu.addAction(act_snap)
        menu.addAction(act_save)
        menu.addSeparator()
        menu.addAction(act_hide)
        menu.addAction(self.manager.exit_action(self))
        with self.manager.suspend_overlay_restore():
            menu.exec(event.globalPos())


class ClockManager:
    def __init__(self, app: QApplication, cfg: dict, autostart: AutostartController | None = None):
        self.app = app
        self.cfg = cfg
        self.autostart = autostart or default_autostart_controller()
        self.restore_suspended = 0
        self.line_window: LineClockWindow | None = None
        self.detached_windows: dict[str, SingleClockWindow] = {}
        self.tray_autostart_action: QAction | None = None

        self.tray = QSystemTrayIcon()
        self.tray.setIcon(self.app.style().standardIcon(QStyle.SP_ComputerIcon))
        self.tray.setToolTip(APP_NAME)
        self.build_tray_menu()
        self.tray.activated.connect(self.on_tray_activated)
        self.tray.show()
        self.sync_windows()

    @contextmanager
    def suspend_overlay_restore(self):
        self.restore_suspended += 1
        try:
            yield
        finally:
            self.restore_suspended = max(0, self.restore_suspended - 1)

    def enabled_cities(self) -> list[dict]:
        return [city for city in self.cfg.get("cities", []) if city.get("enabled", False)]

    def line_cities(self) -> list[dict]:
        return [city for city in self.enabled_cities() if city.get("placement") == PLACEMENT_LINE]

    def detached_cities(self) -> list[dict]:
        return [city for city in self.enabled_cities() if city.get("placement") == PLACEMENT_WINDOW]

    def build_tray_menu(self) -> None:
        menu = QMenu()

        act_show = QAction("Show all clocks", self.app)
        act_show.triggered.connect(self.show_all)
        act_hide = QAction("Hide all clocks", self.app)
        act_hide.triggered.connect(self.hide_all)
        act_manage = QAction("Add or remove clocks...", self.app)
        act_manage.triggered.connect(self.select_cities)
        act_reload = QAction("Reload config", self.app)
        act_reload.triggered.connect(self.reload_config)
        act_black = QAction("Theme: Black", self.app)
        act_black.triggered.connect(lambda: self.set_theme("black"))
        act_white = QAction("Theme: White", self.app)
        act_white.triggered.connect(lambda: self.set_theme("white"))
        act_exit = QAction("Exit", self.app)
        act_exit.triggered.connect(self.exit_requested)
        self.tray_autostart_action = self._make_autostart_action(menu)

        menu.addAction(act_show)
        menu.addAction(act_hide)
        menu.addAction(act_manage)
        menu.addAction(act_reload)
        menu.addAction(act_black)
        menu.addAction(act_white)
        menu.addAction(self.tray_autostart_action)
        menu.addSeparator()
        menu.addAction(act_exit)
        menu.aboutToShow.connect(lambda: self._sync_autostart_action(self.tray_autostart_action))
        self.tray.setContextMenu(menu)

    def _make_autostart_action(self, parent) -> QAction:
        action = QAction(AUTOSTART_ACTION_TEXT, parent)
        action.setCheckable(True)
        action.triggered.connect(self._on_autostart_triggered)
        self._sync_autostart_action(action)
        return action

    def _sync_autostart_action(self, action: QAction | None) -> None:
        if action is None:
            return
        action.setEnabled(self.autostart.supported)
        action.blockSignals(True)
        action.setChecked(self.autostart.is_enabled())
        action.blockSignals(False)
        action.setToolTip(self.autostart.tooltip())

    def _on_autostart_triggered(self, checked: bool = False) -> None:
        try:
            self.autostart.set_enabled(bool(checked))
        except OSError as exc:
            with self.suspend_overlay_restore():
                show_message(QMessageBox.Warning, APP_NAME, f"Could not update Start with Windows.\n{exc}")
        sender = self.sender()
        if isinstance(sender, QAction):
            self._sync_autostart_action(sender)
        if self.tray_autostart_action is not None and sender is not self.tray_autostart_action:
            self._sync_autostart_action(self.tray_autostart_action)

    def populate_common_menu(self, menu: QMenu) -> None:
        act_manage = QAction("Add or remove clocks...", menu)
        act_manage.triggered.connect(self.select_cities)
        act_seconds = QAction("Show / Hide seconds", menu)
        act_seconds.triggered.connect(self.toggle_seconds)
        act_24h = QAction("Switch 24h / 12h", menu)
        act_24h.triggered.connect(self.toggle_24h)
        act_reload = QAction("Reload config", menu)
        act_reload.triggered.connect(self.reload_config)
        act_black = QAction("Theme: Black", menu)
        act_black.triggered.connect(lambda: self.set_theme("black"))
        act_white = QAction("Theme: White", menu)
        act_white.triggered.connect(lambda: self.set_theme("white"))

        menu.addAction(act_manage)
        menu.addSeparator()
        menu.addAction(act_seconds)
        menu.addAction(act_24h)
        menu.addAction(act_reload)
        menu.addAction(act_black)
        menu.addAction(act_white)
        menu.addAction(self._make_autostart_action(menu))

    def exit_action(self, parent: QWidget) -> QAction:
        action = QAction("Exit", parent)
        action.triggered.connect(self.exit_requested)
        return action

    def sync_windows(self) -> None:
        line_cities = self.line_cities()
        detached_cities = self.detached_cities()
        detached_keys = {city_key(city) for city in detached_cities}

        for index, city in enumerate(self.cfg.get("cities", [])):
            ensure_city_window(city, index)
            city["window"]["offset_index"] = index

        if line_cities:
            if self.line_window is None:
                self.line_window = LineClockWindow(self)
            else:
                self.line_window.rebuild_cards()
                self.line_window.apply_window_flags()
                self.line_window.apply_theme()
                min_width, min_height = self.line_window.minimum_line_size()
                saved_width = int(self.cfg["window"].get("width", min_width))
                saved_height = int(self.cfg["window"].get("height", min_height))
                self.line_window.setMinimumSize(min_width, min_height)
                self.line_window.resize(max(min_width, saved_width), max(min_height, saved_height))
                self.line_window.show()
                self.line_window.refresh_times()
        elif self.line_window is not None:
            self.line_window.hide()
            self.line_window.deleteLater()
            self.line_window = None

        for key in list(self.detached_windows):
            if key not in detached_keys:
                self.detached_windows[key].hide()
                self.detached_windows[key].deleteLater()
                del self.detached_windows[key]

        for city in detached_cities:
            key = city_key(city)
            if key not in self.detached_windows:
                self.detached_windows[key] = SingleClockWindow(self, city)
            else:
                window = self.detached_windows[key]
                window.city = city
                window.window_cfg = ensure_city_window(city, city.get("window", {}).get("offset_index", 0))
                window.apply_window_flags()
                window.card.display_cfg = self.cfg["display"]
                window.card.scale = float(window.window_cfg.get("scale", 1.0))
                window.apply_theme()
                min_width, min_height = window.minimum_clock_size()
                saved_width = int(window.window_cfg.get("width", DEFAULT_CITY_WIDTH))
                saved_height = int(window.window_cfg.get("height", DEFAULT_CITY_HEIGHT))
                window.setMinimumSize(min_width, min_height)
                window.resize(max(min_width, saved_width), max(min_height, saved_height))
                window.show()
                window.card.refresh_time()

        save_config(self.cfg)

    def refresh_all_windows(self) -> None:
        self.sync_windows()
        if self.line_window is not None:
            self.line_window.apply_theme()
            self.line_window.refresh_times()
        for window in self.detached_windows.values():
            window.apply_theme()
            window.card.refresh_time()

    def toggle_seconds(self) -> None:
        self.cfg["display"]["show_seconds"] = not self.cfg["display"].get("show_seconds", False)
        save_config(self.cfg)
        self.refresh_all_windows()

    def toggle_24h(self) -> None:
        self.cfg["display"]["use_24h"] = not self.cfg["display"].get("use_24h", True)
        save_config(self.cfg)
        self.refresh_all_windows()

    def set_theme(self, theme_name: str) -> None:
        self.cfg["display"]["theme"] = theme_name
        save_config(self.cfg)
        self.refresh_all_windows()

    def reload_config(self) -> None:
        with self.suspend_overlay_restore():
            try:
                loaded = normalize_config(load_config())
            except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
                show_message(QMessageBox.Critical, "Configuration error", str(exc))
                return
        self.cfg = loaded
        self.refresh_all_windows()

    def apply_selected_cities(self, mapping: dict[str, str]) -> None:
        for city in self.cfg.get("cities", []):
            placement = mapping.get(city_key(city), PLACEMENT_OFF)
            city["placement"] = placement
            city["enabled"] = placement != PLACEMENT_OFF

        save_config(self.cfg)
        self.refresh_all_windows()
        self.show_all()

    def select_cities(self) -> None:
        dialog = CitySelectionDialog(self.cfg.get("cities", []), on_apply=self.apply_selected_cities)
        with self.suspend_overlay_restore():
            dialog.exec()

    def remove_clock(self, key: str) -> None:
        for city in self.cfg.get("cities", []):
            if city_key(city) == key:
                city["placement"] = PLACEMENT_OFF
                city["enabled"] = False
                break
        self.refresh_all_windows()

    def show_all(self) -> None:
        if self.line_window is not None:
            self.line_window.show()
            self.line_window.raise_()
        for window in self.detached_windows.values():
            window.show()
            window.raise_()

    def hide_all(self) -> None:
        if self.line_window is not None:
            self.line_window.hide()
        for window in self.detached_windows.values():
            window.hide()

    def any_visible(self) -> bool:
        return (self.line_window is not None and self.line_window.isVisible()) or any(
            window.isVisible() for window in self.detached_windows.values()
        )

    def on_tray_activated(self, reason) -> None:
        if reason == QSystemTrayIcon.Trigger:
            if self.any_visible():
                self.hide_all()
            else:
                self.show_all()

    def exit_requested(self) -> None:
        self.hide_all()
        self.tray.hide()
        save_config_immediate(self.cfg)
        self.app.quit()


def main() -> int:
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    instance = claim_single_instance()
    if instance is None:
        show_message(QMessageBox.Information, APP_NAME, f"{APP_NAME} is already running.")
        return 0
    # Keep the server referenced for the life of the process.
    app._single_instance_server = instance

    try:
        ensure_config_next_to_exe()
        cfg = normalize_config(load_config())
    except (OSError, ValueError, TypeError, AttributeError, KeyError) as exc:
        show_message(QMessageBox.Critical, "Configuration error", str(exc))
        return 1

    _manager = ClockManager(app, cfg)
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
