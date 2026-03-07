"""
overlay.py — Read-only analysis overlay for Minesweeper.

Captures the screen, runs the existing solver, and draws coloured markers on
top of the browser so the human player can see what is safe, what is a mine,
and what is ambiguous.  Never clicks anything.

Usage:
    python overlay.py
"""

import sys
import tkinter as tk

import cv2
import mss
import numpy as np

from capture import capture_board
from board_parser import parse_board, UNKNOWN, FLAGGED
from solver import solve

# ── Overlay colours ────────────────────────────────────────────────────────────
COLOR_SAFE      = "#00FF00"   # green  — safe cells
COLOR_MINE      = "#FF3333"   # red    — mine cells
COLOR_AMBIGUOUS = "#FFD700"   # yellow — ambiguous cells
COLOR_FLAGGED   = "#FF8800"   # orange — already-flagged cells

OUTLINE_WIDTH = 3
LABEL_FONT    = ("Arial", 7, "bold")

# ── Grid auto-detection parameters ────────────────────────────────────────────
CELL_COLORS_BGR = [
    (192, 192, 192),   # unrevealed cell
    (224, 224, 224),   # revealed/empty cell
]
CELL_TOLERANCE  = 18                 # ± per channel
DEFAULT_ROWS    = 16
DEFAULT_COLS    = 30


# ── Screen picker ──────────────────────────────────────────────────────────────

def pick_monitor() -> dict:
    """
    List all connected monitors and let the user choose one.
    Returns the mss monitor dict for the chosen screen.
    """
    with mss.mss() as sct:
        # mss.monitors[0] is the virtual combined desktop; real monitors start at index 1
        monitors = sct.monitors[1:]

    if not monitors:
        print("No monitors detected — using full virtual desktop.")
        with mss.mss() as sct:
            return sct.monitors[0]

    print("Available screens:")
    for i, m in enumerate(monitors, start=1):
        print(f"  [{i}] Screen {i} — {m['width']}×{m['height']} at offset ({m['left']}, {m['top']})")

    while True:
        try:
            choice = int(input("Select screen number: ").strip())
            if 1 <= choice <= len(monitors):
                return monitors[choice - 1]
        except (ValueError, EOFError):
            pass
        print(f"Please enter a number between 1 and {len(monitors)}.")


# ── Board auto-detection ───────────────────────────────────────────────────────

def detect_board_region(img_rgb: np.ndarray) -> tuple[int, int, int, int, int, int]:
    """
    Scan a full-screen RGB image for the minesweeper grid.

    Returns (board_x, board_y, board_w, board_h, rows, cols) where
    board_x/y are pixel offsets within the captured image (i.e. relative to
    the chosen monitor's top-left corner).

    Falls back to (0, 0, img_w, img_h, DEFAULT_ROWS, DEFAULT_COLS) on failure.
    """
    img_h, img_w = img_rgb.shape[:2]
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)

    # Build a union mask of both cell colours
    mask = np.zeros(img_bgr.shape[:2], dtype=np.uint8)
    for color in CELL_COLORS_BGR:
        lo = np.array([max(0, c - CELL_TOLERANCE) for c in color], dtype=np.uint8)
        hi = np.array([min(255, c + CELL_TOLERANCE) for c in color], dtype=np.uint8)
        mask = cv2.bitwise_or(mask, cv2.inRange(img_bgr, lo, hi))

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

    if not contours:
        return 0, 0, img_w, img_h, DEFAULT_ROWS, DEFAULT_COLS

    # Keep only roughly-square blobs that are plausibly cell-sized (8–80 px per side)
    rects = []
    for cnt in contours:
        x, y, w, h = cv2.boundingRect(cnt)
        if w < 8 or h < 8 or w > 80 or h > 80:
            continue
        aspect = w / h
        if not (0.5 < aspect < 2.0):
            continue
        rects.append((x, y, w, h))

    if not rects:
        return 0, 0, img_w, img_h, DEFAULT_ROWS, DEFAULT_COLS

    # Estimate cell size as the median width/height of detected blobs
    widths  = sorted(r[2] for r in rects)
    heights = sorted(r[3] for r in rects)
    cell_w  = int(np.median(widths))
    cell_h  = int(np.median(heights))

    if cell_w < 4 or cell_h < 4:
        return 0, 0, img_w, img_h, DEFAULT_ROWS, DEFAULT_COLS

    # Cluster blob top-left corners to a grid
    xs = sorted(set(round(r[0] / cell_w) * cell_w for r in rects))
    ys = sorted(set(round(r[1] / cell_h) * cell_h for r in rects))

    if not xs or not ys:
        return 0, 0, img_w, img_h, DEFAULT_ROWS, DEFAULT_COLS

    board_x = min(r[0] for r in rects)
    board_y = min(r[1] for r in rects)
    board_x_end = max(r[0] + r[2] for r in rects)
    board_y_end = max(r[1] + r[3] for r in rects)

    board_w = board_x_end - board_x
    board_h = board_y_end - board_y

    cols = max(1, round(board_w / cell_w))
    rows = max(1, round(board_h / cell_h))

    return board_x, board_y, board_w, board_h, rows, cols


# ── Overlay window ─────────────────────────────────────────────────────────────

class MinesweeperOverlay:
    """
    Fullscreen, always-on-top, borderless, transparent tkinter overlay.
    Refreshes every 500 ms.  Press ESC to quit.
    """

    def __init__(self, monitor: dict) -> None:
        self._monitor = monitor
        self._region: dict = {
            "top":    monitor["top"],
            "left":   monitor["left"],
            "width":  monitor["width"],
            "height": monitor["height"],
        }

        self._root = tk.Tk()
        self._setup_window()
        self._canvas = tk.Canvas(
            self._root,
            bg="black",
            highlightthickness=0,
        )
        self._canvas.pack(fill=tk.BOTH, expand=True)

        self._status_var = tk.StringVar()
        self._status_label = tk.Label(
            self._root,
            textvariable=self._status_var,
            bg="#222222",
            fg="white",
            font=("Arial", 9, "bold"),
            anchor="w",
            padx=6,
            pady=2,
        )
        self._status_label.place(x=0, y=0)

        self._root.bind("<Escape>", lambda _: self._root.destroy())

        self._apply_click_through()
        self._refresh()

    # ── Window setup ──────────────────────────────────────────────────────────

    def _setup_window(self) -> None:
        root = self._root
        m    = self._monitor
        w, h = m["width"], m["height"]
        left, top = m["left"], m["top"]

        root.title("Minesweeper Overlay")
        root.geometry(f"{w}x{h}+{left}+{top}")
        root.configure(bg="black")
        root.attributes("-topmost", True)
        root.overrideredirect(True)           # borderless
        root.attributes("-transparentcolor", "black")  # black → see-through
        root.attributes("-alpha", 1.0)

    def _apply_click_through(self) -> None:
        """Make the overlay window pass mouse clicks through to windows beneath it."""
        try:
            import win32gui
            import win32con

            hwnd = self._root.winfo_id()
            style = win32gui.GetWindowLong(hwnd, win32con.GWL_EXSTYLE)
            win32gui.SetWindowLong(
                hwnd,
                win32con.GWL_EXSTYLE,
                style | win32con.WS_EX_LAYERED | win32con.WS_EX_TRANSPARENT,
            )
        except Exception as exc:
            print(f"[overlay] click-through not available: {exc}")

    # ── Refresh cycle ─────────────────────────────────────────────────────────

    def _refresh(self) -> None:
        try:
            self._draw()
        except Exception as exc:
            print(f"[overlay] refresh error: {exc}")
        self._root.after(500, self._refresh)

    def _draw(self) -> None:
        canvas = self._canvas
        canvas.delete("all")

        # 1. Capture full screen of chosen monitor
        img_rgb = capture_board(self._region)

        # 2. Auto-detect board region every cycle (adapts to window moves/resizes)
        bx, by, bw, bh, rows, cols = detect_board_region(img_rgb)

        # 3. Crop the board area and parse
        board_img = img_rgb[by : by + bh, bx : bx + bw]
        if board_img.size == 0:
            self._status_var.set("⚠ Board not detected")
            return

        board = parse_board(board_img, rows, cols)

        # 4. Run solver (no mine counter available without calibration)
        safe_cells, mine_cells, ambiguous = solve(board)

        # 5. Draw outlines
        n_safe      = len(safe_cells)
        n_mines     = len(mine_cells)
        n_ambiguous = len(ambiguous)
        n_flagged   = 0
        ambiguous_set = set(ambiguous)

        # Pre-compute integer cell dimensions once per refresh
        cell_pw_i = bw / cols
        cell_ph_i = bh / rows

        for r in range(rows):
            for c in range(cols):
                cell_state = board[r][c]

                if cell_state == FLAGGED:
                    color = COLOR_FLAGGED
                    label = "F"
                    n_flagged += 1
                elif (r, c) in mine_cells:
                    color = COLOR_MINE
                    label = "✗"
                elif (r, c) in safe_cells:
                    color = COLOR_SAFE
                    label = "✓"
                elif (r, c) in ambiguous_set:
                    color = COLOR_AMBIGUOUS
                    label = "?"
                else:
                    continue  # revealed/numbered cell — nothing to draw

                # Convert grid position to canvas (screen) coordinates
                x1 = bx + c * cell_pw_i
                y1 = by + r * cell_ph_i
                x2 = bx + (c + 1) * cell_pw_i
                y2 = by + (r + 1) * cell_ph_i
                cx = (x1 + x2) / 2
                cy = (y1 + y2) / 2

                canvas.create_rectangle(
                    x1, y1, x2, y2,
                    outline=color,
                    width=OUTLINE_WIDTH,
                    fill="",        # transparent interior
                )
                canvas.create_text(
                    cx, cy,
                    text=label,
                    fill=color,
                    font=LABEL_FONT,
                )

        # 6. Update status bar
        self._status_var.set(
            f"🟢 Safe: {n_safe}  🔴 Mines: {n_mines}  🟡 Ambiguous: {n_ambiguous}"
            f"  🟠 Flagged: {n_flagged}  |  ESC to quit"
        )

    # ── Entry point ───────────────────────────────────────────────────────────

    def run(self) -> None:
        self._root.mainloop()


# ── Main ───────────────────────────────────────────────────────────────────────

def main() -> None:
    monitor = pick_monitor()
    print(
        f"\nStarting overlay on {monitor['width']}×{monitor['height']} "
        f"at ({monitor['left']}, {monitor['top']}) …"
    )
    app = MinesweeperOverlay(monitor)
    app.run()


if __name__ == "__main__":
    main()
