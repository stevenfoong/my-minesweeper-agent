import mss
import numpy as np
from PIL import Image

def capture_board(region: dict) -> np.ndarray:
    """
    Captures the minesweeper board from screen.
    region = {"top": y, "left": x, "width": w, "height": h}
    Returns an RGB numpy array.
    """
    with mss.mss() as sct:
        raw = sct.grab(region)
        img = Image.frombytes("RGB", raw.size, raw.bgra, "raw", "BGRX")
        return np.array(img)

def save_screenshot(img: np.ndarray, path="debug_board.png"):
    """Save board screenshot for debugging."""
    from PIL import Image
    Image.fromarray(img).save(path)
    print(f"Screenshot saved to {path}")
