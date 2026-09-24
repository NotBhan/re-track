"""Parent process watchdog for RE:Track HTTP backend.

Ensures the Python backend process terminates cleanly if its parent Tauri
or CLI wrapper process terminates abruptly.
"""

import logging
import os
import signal
import threading
import time

logger = logging.getLogger(__name__)


def start_parent_watchdog() -> None:
    """Launch a background thread to terminate backend if parent process dies abruptly."""
    parent_pid_str = os.environ.get("RETRACK_PARENT_PID")
    if not parent_pid_str:
        return
    try:
        parent_pid = int(parent_pid_str)
    except ValueError:
        return

    def _watchdog_loop() -> None:
        while True:
            time.sleep(1.0)
            try:
                current_ppid = os.getppid()
                if current_ppid != parent_pid:
                    logger.warning(
                        "Parent process %d terminated (current ppid=%d). Terminating orphaned backend.",
                        parent_pid,
                        current_ppid,
                    )
                    os.kill(os.getpid(), signal.SIGTERM)
                    break
                # Verify parent process still exists
                os.kill(parent_pid, 0)
            except (ProcessLookupError, PermissionError):
                logger.warning(
                    "Parent process %d is no longer reachable. Terminating orphaned backend.",
                    parent_pid,
                )
                os.kill(os.getpid(), signal.SIGTERM)
                break

    thread = threading.Thread(target=_watchdog_loop, name="retrack-parent-watchdog", daemon=True)
    thread.start()
    logger.info("Parent-death watchdog thread registered for parent PID %d", parent_pid)
