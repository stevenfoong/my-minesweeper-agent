import cv2
import numpy as np

# ── Cell state constants ──────────────────────────────────────────────────────
UNKNOWN  = -1   # unrevealed cell
FLAGGED  = -2   # flagged as mine
EXPLODED = -3   # mine that was clicked — red background (game over)
EMPTY    =  0   # revealed, no adjacent mines
# 1–8 = number of adjacent mines

# ── minesweeper.online color profiles (RGB) ───────────────────────────────────
# These are sampled from the site at default zoom (100%)
CELL_COLORS = {
    "unrevealed": (192, 192, 192),   # silver/grey unrevealed cell
    "revealed":   (224, 224, 224),   # lighter grey revealed empty
    "flag_red":   (255,   0,   0),   # red flag marker
}

# Number colors on the site (center pixel of digit area)
NUMBER_COLORS_BGR = {
    1: (255,   0,   0),   # Blue   (BGR)
    2: (  0, 128,   0),   # Green
    3: (  0,   0, 255),   # Red
    4: (128,   0,   0),   # Dark Blue
    5: (  0,   0, 128),   # Dark Red
    6: (  0, 128, 128),   # Cyan
    7: (  0,   0,   0),   # Black
    8: (128, 128, 128),   # Grey
}

def classify_cell(cell_bgr: np.ndarray) -> int:
    """
    Classify a single 32x32 cell image.
    Uses color matching against known minesweeper.online palette.
    """
    h, w = cell_bgr.shape[:2]

    # --- Check for exploded mine: most of the cell background is red ---
    # (The mine that was clicked has a solid red background, unlike a flag
    #  which only has a small red flag icon in the centre.)
    total_pixels = h * w
    red_pixels_all = np.sum(
        (cell_bgr[:, :, 2] > 150) &   # high red channel  (BGR index 2)
        (cell_bgr[:, :, 1] < 100) &   # low green channel (BGR index 1)
        (cell_bgr[:, :, 0] < 100)     # low blue channel  (BGR index 0)
    )
    if red_pixels_all > total_pixels * 0.25:
        return EXPLODED

    # --- Check for flag (look for red pixels in center region) ---
    center = cell_bgr[h//4:3*h//4, w//4:3*w//4]
    red_pixels = np.sum(
        (center[:,:,2] > 180) &   # high red
        (center[:,:,1] < 80)  &   # low green
        (center[:,:,0] < 80)       # low blue
    )
    if red_pixels > 20:
        return FLAGGED

    # --- Check overall brightness to distinguish revealed vs unrevealed ---
    avg = cell_bgr.mean()

    # Unrevealed cells have a raised 3D border — check corner brightness variance
    corners = [
        cell_bgr[2, 2],
        cell_bgr[2, w-3],
        cell_bgr[h-3, 2],
        cell_bgr[h-3, w-3],
    ]
    corner_brightness = [c.mean() for c in corners]
    brightness_range = max(corner_brightness) - min(corner_brightness)

    # Unrevealed cells have high contrast 3D borders
    if brightness_range > 60:
        return UNKNOWN

    # Revealed cell — check for number by sampling center pixel color
    cx, cy = w // 2, h // 2
    sample_region = cell_bgr[cy-4:cy+4, cx-4:cx+4]
    avg_color = sample_region.mean(axis=(0, 1))  # BGR

    best_match = EMPTY
    best_dist  = 80  # minimum color distance threshold

    for num, color_bgr in NUMBER_COLORS_BGR.items():
        dist = np.sqrt(sum((float(avg_color[i]) - color_bgr[i])**2 for i in range(3)))
        if dist < best_dist:
            best_dist  = dist
            best_match = num

    return best_match

def parse_board(img_rgb: np.ndarray, rows: int, cols: int) -> list[list[int]]:
    """
    Split board image into grid cells and classify each one.
    Returns 2D list of cell states.
    """
    img_bgr = cv2.cvtColor(img_rgb, cv2.COLOR_RGB2BGR)
    cell_h = img_bgr.shape[0] // rows
    cell_w = img_bgr.shape[1] // cols
    board = []

    for r in range(rows):
        row = []
        for c in range(cols):
            y1, y2 = r * cell_h, (r + 1) * cell_h
            x1, x2 = c * cell_w, (c + 1) * cell_w
            cell = img_bgr[y1:y2, x1:x2]
            state = classify_cell(cell)
            row.append(state)
        board.append(row)

    return board

def print_board(board: list[list[int]]):
    """Debug: print board to console."""
    symbols = {-1: "?", -2: "F", -3: "X", 0: "."}
    for row in board:
        print(" ".join(symbols.get(c, str(c)) for c in row))

def is_game_over(board: list[list[int]]) -> bool:
    """Return True if an exploded mine is present on the board (game lost)."""
    return any(cell == EXPLODED for row in board for cell in row)
