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

# ── Mine counter (7-segment LED display) parsing ──────────────────────────────

# 7-segment encoding: segments are labeled a-g in standard order
# Segment positions (relative to a digit bounding box):
#   aaa
#  f   b
#  f   b
#   ggg
#  e   c
#  e   c
#   ddd
#
# Each key is a frozenset of lit segment names, value is the digit

_SEG_TO_DIGIT = {
    frozenset('abcdef'):   0,
    frozenset('bc'):       1,
    frozenset('abdeg'):    2,
    frozenset('abcdg'):    3,
    frozenset('bcfg'):     4,
    frozenset('acdfg'):    5,
    frozenset('acdefg'):   6,
    frozenset('abc'):      7,
    frozenset('abcdefg'):  8,
    frozenset('abcdfg'):   9,
}

def _check_segment(region: np.ndarray, threshold: float = 0.15) -> bool:
    """Return True if a segment region has enough red pixels to be considered lit."""
    # Red pixels: high R, low G, low B  (image is RGB)
    red_mask = (
        (region[:, :, 0] > 150) &
        (region[:, :, 1] < 80)  &
        (region[:, :, 2] < 80)
    )
    return red_mask.mean() > threshold

def _classify_digit(digit_img: np.ndarray) -> int | None:
    """
    Given a ~H x W RGB image of a single 7-segment digit,
    determine which digit it represents using segment zone sampling.
    Returns 0-9 or None if unrecognised.
    """
    h, w = digit_img.shape[:2]
    if h < 10 or w < 5:
        return None

    # Divide into thirds vertically (top / mid / bot) and halves horizontally (left / right)
    t1, t2 = h // 3, 2 * h // 3
    m = h // 2

    # Segment zones (approximate):
    seg_a = digit_img[0:t1//2,          w//4:3*w//4]    # top horizontal
    seg_d = digit_img[t2+t1//2:h,       w//4:3*w//4]    # bottom horizontal
    seg_g = digit_img[m-t1//6:m+t1//6,  w//4:3*w//4]    # middle horizontal
    seg_b = digit_img[0:t2,             3*w//4:w]        # top-right vertical
    seg_c = digit_img[t1:h,             3*w//4:w]        # bottom-right vertical
    seg_f = digit_img[0:t2,             0:w//4]          # top-left vertical
    seg_e = digit_img[t1:h,             0:w//4]          # bottom-left vertical

    lit = set()
    for name, zone in [('a', seg_a), ('b', seg_b), ('c', seg_c),
                        ('d', seg_d), ('e', seg_e), ('f', seg_f), ('g', seg_g)]:
        if zone.size > 0 and _check_segment(zone):
            lit.add(name)

    return _SEG_TO_DIGIT.get(frozenset(lit))

def parse_mine_counter(img_rgb: np.ndarray) -> int | None:
    """
    Parse the 7-segment mine counter display image.
    Returns the integer value (may be negative if over-flagged), or None on failure.

    The display shows: total_mines - flags_placed
    - Positive: mines still to flag
    - Zero: all mines flagged, all remaining unknowns are safe
    - Negative: over-flagged (shouldn't happen with correct solver)
    """
    if img_rgb is None or img_rgb.size == 0:
        return None

    h, w = img_rgb.shape[:2]

    # Check for negative sign: leftmost ~15% of width, middle vertical strip has red pixels
    # Use a lower threshold (0.05) than segment detection because the sign region is
    # narrow and may contain fewer lit pixels than a full digit segment.
    sign_region = img_rgb[:, :w//6, :]
    is_negative = _check_segment(sign_region, threshold=0.05)

    # Remaining width is the digit area — split into 3 equal digit slots
    digit_area = img_rgb[:, w//6:, :]
    dw = digit_area.shape[1] // 3

    digits = []
    for i in range(3):
        d_img = digit_area[:, i*dw:(i+1)*dw, :]
        d = _classify_digit(d_img)
        if d is None:
            # Could be a blank/leading zero — treat as 0
            d = 0
        digits.append(d)

    value = digits[0] * 100 + digits[1] * 10 + digits[2]
    return -value if is_negative else value
