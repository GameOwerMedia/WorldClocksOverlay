import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication


@pytest.fixture(scope="session")
def qapp():
    application = QApplication.instance() or QApplication([])
    yield application


@pytest.fixture(autouse=True)
def _reset_clock_save_state(monkeypatch):
    """Stop a debounced save before the config-path patch is removed."""
    yield
    import app

    timer = app._save_timer
    if timer is not None and timer.isActive():
        timer.stop()
    app._save_pending_cfg = None
