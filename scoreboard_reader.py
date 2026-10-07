"""Capture the visible League scoreboard on Tab. OCR is untrusted dated evidence."""
from __future__ import annotations
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import queue
import subprocess
import threading
import time
import uuid

ROOT = Path(__file__).parent


def foreground_league_rect():
    """Return only the foreground game client rectangle; never screenshot the desktop."""
    if os.name != "nt":
        return None
    user = ctypes.WinDLL("user32", use_last_error=True)
    kernel = ctypes.WinDLL("kernel32", use_last_error=True)
    user.GetForegroundWindow.restype = wintypes.HWND
    user.GetWindowThreadProcessId.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.DWORD)]
    kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
    kernel.OpenProcess.restype = wintypes.HANDLE
    kernel.QueryFullProcessImageNameW.argtypes = [wintypes.HANDLE, wintypes.DWORD, wintypes.LPWSTR, ctypes.POINTER(wintypes.DWORD)]
    kernel.CloseHandle.argtypes = [wintypes.HANDLE]
    user.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.POINT)]
    window = user.GetForegroundWindow()
    pid = wintypes.DWORD()
    user.GetWindowThreadProcessId(window, ctypes.byref(pid))
    process = kernel.OpenProcess(0x1000, False, pid.value)
    if not process:
        return None
    try:
        size = wintypes.DWORD(32768)
        name = ctypes.create_unicode_buffer(size.value)
        if not kernel.QueryFullProcessImageNameW(process, 0, name, ctypes.byref(size)):
            return None
        if Path(name.value).name.casefold() != "league of legends.exe":
            return None
    finally:
        kernel.CloseHandle(process)
    rect, origin = wintypes.RECT(), wintypes.POINT(0, 0)
    if not user.GetClientRect(window, ctypes.byref(rect)) or not user.ClientToScreen(window, ctypes.byref(origin)):
        return None
    width, height = rect.right - rect.left, rect.bottom - rect.top
    if width < 640 or height < 480:
        return None
    return {"left": origin.x, "top": origin.y, "width": width, "height": height}


def match_identity(state):
    # A restarted Practice Tool match can have the same roster. Timestamp rollback invalidates it.
    return tuple(sorted((str(p.get("name")), str(p.get("champion")), str(p.get("team")))
                        for p in state.get("players", [])))


def ocr_image(path: Path):
    result = subprocess.run(["powershell.exe", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                             "-File", str(ROOT / "scoreboard_ocr.ps1"), str(path.resolve())],
                            capture_output=True, timeout=15, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    if result.returncode:
        raise RuntimeError("Windows OCR failed")
    data = json.loads(result.stdout.decode("utf-8-sig"))
    if not isinstance(data.get("text"), str):
        raise ValueError("OCR result missing text")
    return data


class ScoreboardWatcher:
    def __init__(self, live_state, root=ROOT / "artifacts/scoreboards"):
        self.live_state = live_state
        self.root = Path(root)
        self.key = int(os.getenv("COACH_SCOREBOARD_VK", "0x09"), 0)
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.work = queue.Queue(maxsize=2)
        self.latest = None
        self.error = ""
        self.captures = 0
        self.threads = []

    def start(self):
        self.root.mkdir(parents=True, exist_ok=True)
        for target in (self._watch, self._read):
            thread = threading.Thread(target=target, daemon=True, name="coach-scoreboard")
            self.threads.append(thread)
            thread.start()

    def stop(self):
        self.stop_event.set()

    def _watch(self):
        import mss
        import mss.tools
        try:
            with mss.mss() as screen:
                previous = False
                while not self.stop_event.is_set():
                    down = bool(ctypes.windll.user32.GetAsyncKeyState(self.key) & 0x8000)
                    if down and not previous and foreground_league_rect():
                        # Wait for the scoreboard animation, then recheck foreground and key.
                        if self.stop_event.wait(.18):
                            break
                        rect = foreground_league_rect()
                        if rect and ctypes.windll.user32.GetAsyncKeyState(self.key) & 0x8000:
                            self.capture(screen, rect)
                    previous = down
                    self.stop_event.wait(.015)
        except Exception as exc:
            self.error = f"Capture failed: {type(exc).__name__}"

    def capture(self, screen, rect):
        import mss.tools
        # Live data is checked before each capture; screenshots outside matches are discarded.
        try:
            state = self.live_state()
        except Exception:
            return
        if not state or not state.get("players"):
            return
        override = os.getenv("COACH_SCOREBOARD_RECT", "")
        if override:
            x, y, width, height = map(int, override.split(","))
            if x < 0 or y < 0 or width < 1 or height < 1 or x + width > rect["width"] or y + height > rect["height"]:
                raise ValueError("Scoreboard crop must stay inside the game window")
        else:
            x, y = int(rect["width"] * .12), int(rect["height"] * .12)
            width, height = int(rect["width"] * .76), int(rect["height"] * .76)
        cropped = {"left": rect["left"] + x, "top": rect["top"] + y, "width": width, "height": height}
        # The API read may take time. Never capture a different window after an alt-tab.
        if foreground_league_rect() != rect or not ctypes.windll.user32.GetAsyncKeyState(self.key) & 0x8000:
            return
        shot = screen.grab(cropped)
        if foreground_league_rect() != rect:
            return
        path = self.root / f"scoreboard-{time.time_ns()}-{uuid.uuid4().hex[:8]}.png"
        mss.tools.to_png(shot.rgb, shot.size, output=str(path))
        record = {"path": str(path), "captured_at": time.time(), "monotonic": time.monotonic(),
                  "game_second": state.get("game_time_seconds", 0), "match": match_identity(state),
                  "source": "visible scoreboard opened with configured key", "status": "pending OCR"}
        with self.lock:
            self.latest = record
            self.captures += 1
        try:
            self.work.put_nowait(record)
        except queue.Full:
            record["status"] = "OCR queue full; image saved"
        # Bounded retention: only this watcher's own named PNG artifacts.
        for old in sorted(self.root.glob("scoreboard-*.png"))[:-20]:
            try:
                old.unlink()
            except OSError:
                pass

    def _read(self):
        while not self.stop_event.is_set():
            try:
                record = self.work.get(timeout=.2)
            except queue.Empty:
                continue
            try:
                result = ocr_image(Path(record["path"]))
                status = "OCR read" if result["text"].strip() else "No readable scoreboard text"
                values = {"ocr_text": result["text"][:6000], "lines": result.get("lines", [])[:80],
                          "language": result.get("language"), "status": status}
            except Exception as exc:
                values = {"status": f"OCR failed: {type(exc).__name__}"}
                self.error = values["status"]
            with self.lock:
                record.update(values)
            self.work.task_done()

    def snapshot(self, state, max_age=45):
        with self.lock:
            record = dict(self.latest) if self.latest else None
        if not record or record["match"] != match_identity(state):
            return None
        if time.monotonic() - record["monotonic"] > max_age or state.get("game_time_seconds", 0) < record["game_second"]:
            return None
        if not record.get("ocr_text"):
            return None
        # File paths and internal identifiers are not sent to the models.
        return {k: record[k] for k in ("captured_at", "game_second", "source", "ocr_text", "lines", "status")} | {
            "reliability": "Unverified OCR, may misread digits or associate text with the wrong player. API data wins. "
                           "Never infer item icons, spell cooldowns, enemy gold, or locations from missing text."}

    def status(self):
        with self.lock:
            latest = dict(self.latest) if self.latest else {}
        age = int(time.monotonic() - latest["monotonic"]) if latest else None
        return {"captures": self.captures, "last_status": latest.get("status", "No scoreboard captured yet"),
                "age_seconds": age, "error": self.error,
                "active": len(self.threads) == 2 and all(t.is_alive() for t in self.threads), "key": hex(self.key)}
