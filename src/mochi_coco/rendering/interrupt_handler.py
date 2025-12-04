import threading
import time
from typing import Optional


class InterruptHandler:
    """Handles stream interruption using a simple timing-based approach."""

    def __init__(self):
        self.interrupt_event = threading.Event()
        self.monitor_thread: Optional[threading.Thread] = None
        self.stop_event = threading.Event()
        self.last_chunk_time = 0.0
        self.chunk_timeout = (
            2.0  # Seconds to wait for next chunk before checking for interrupt
        )

    def start_monitoring(self):
        """Start monitoring for interruption."""
        self.interrupt_event.clear()
        self.stop_event.clear()
        self.last_chunk_time = time.time()

        # Start monitoring thread
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()

    def stop_monitoring(self):
        """Stop monitoring."""
        self.stop_event.set()
        if self.monitor_thread and self.monitor_thread.is_alive():
            self.monitor_thread.join(timeout=0.1)

    def was_interrupted(self) -> bool:
        """Check if interruption was requested."""
        return self.interrupt_event.is_set()

    def update_chunk_received(self):
        """Signal that a new chunk was received."""
        self.last_chunk_time = time.time()

    def request_interrupt(self):
        """Request an interrupt (for testing or external triggers)."""
        self.interrupt_event.set()

    def _monitor_loop(self):
        """Main monitoring loop that checks for keyboard input."""
        import platform

        if platform.system() == "Windows":
            self._monitor_windows()
        else:
            self._monitor_unix()

    def _monitor_windows(self):
        """Windows-specific monitoring using msvcrt."""
        try:
            import msvcrt

            while not self.stop_event.is_set():
                if msvcrt.kbhit():
                    key = msvcrt.getch()
                    if key == b"\x1b":  # ESC key
                        self.interrupt_event.set()
                        break
                time.sleep(0.01)

        except ImportError:
            # msvcrt not available, just wait
            self.stop_event.wait()

    def _monitor_unix(self):
        """Unix-like systems monitoring."""
        try:
            import select
            import sys
            import termios
            import tty

            # Only proceed if we have a proper terminal
            if not sys.stdin.isatty():
                self.stop_event.wait()
                return

            fd = sys.stdin.fileno()
            old_settings = termios.tcgetattr(fd)

            try:
                # Set to cbreak mode (less invasive than raw mode)
                tty.setcbreak(fd)

                while not self.stop_event.is_set():
                    # Non-blocking check for input
                    ready, _, _ = select.select([sys.stdin], [], [], 0.05)
                    if ready:
                        char = sys.stdin.read(1)
                        if ord(char) == 27:  # ESC key
                            self.interrupt_event.set()
                            break

            finally:
                # Always restore terminal settings
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

        except (ImportError, OSError, termios.error):
            # If we can't set up terminal monitoring, just wait
            self.stop_event.wait()
