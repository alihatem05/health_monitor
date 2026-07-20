from unittest.mock import patch
from app.scheduler import handle_alert

class DummyService:
    def __init__(self, name):
        self.name = name

def test_handle_alert_first_check():
    service = DummyService("API")

    with patch("app.scheduler.log") as mock_log:
        handle_alert(service, None, "UP")

    mock_log.assert_called_once_with(
        "INFO",
        "API first check: UP",
    )

def test_handle_alert_status_changed():
    service = DummyService("API")

    with patch("app.scheduler.log") as mock_log:
        handle_alert(service, "UP", "DOWN")

    mock_log.assert_called_once_with(
        "ALERT",
        "API changed: UP -> DOWN",
    )