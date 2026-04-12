from unittest.mock import patch, MagicMock
from gv_gateway.notify import send


def test_send_calls_notify_send():
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        send("Marlin", "buy milk")
        mock_run.assert_called_once_with(["notify-send", "Marlin", "buy milk"])


def test_send_logs_on_failure(caplog):
    import logging
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        with caplog.at_level(logging.WARNING, logger="gv_gateway.notify"):
            send("Marlin", "buy milk")
    assert "notify-send failed" in caplog.text
