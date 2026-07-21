import logging
import subprocess
import sys


class DesktopNotificationService:
    """Best-effort native notifications for Windows and macOS."""

    def __init__(self, app_name="Engraver"):
        self.app_name = app_name

    def notify(self, title, message, timeout=10):
        title = str(title or self.app_name)
        message = str(message or "")
        try:
            from plyer import notification

            notification.notify(
                title=title,
                message=message,
                app_name=self.app_name,
                timeout=timeout,
            )
            return True
        except Exception as exc:
            logging.warning("Plyer notification failed: %s", exc)

        if sys.platform == "darwin":
            return self._notify_macos(title, message)
        return False

    @staticmethod
    def _notify_macos(title, message):
        def escape(value):
            return str(value).replace("\\", "\\\\").replace('"', '\\"')

        script = (
            f'display notification "{escape(message)}" '
            f'with title "{escape(title)}"'
        )
        try:
            subprocess.run(
                ["osascript", "-e", script],
                check=True,
                capture_output=True,
                text=True,
                timeout=10,
            )
            return True
        except (OSError, subprocess.SubprocessError) as exc:
            logging.warning("macOS notification failed: %s", exc)
            return False
