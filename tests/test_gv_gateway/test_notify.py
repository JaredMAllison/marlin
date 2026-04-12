from unittest.mock import patch
from gv_gateway.notify import send


def test_send_calls_notify_send():
    with patch("subprocess.run") as mock_run:
        send("Marlin", "buy milk")
        mock_run.assert_called_once_with(
            ["notify-send", "Marlin", "buy milk"], check=True
        )
