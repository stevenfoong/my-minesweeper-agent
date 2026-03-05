"""
Run this first to find the exact screen region of your minesweeper board.
Move your mouse to the TOP-LEFT corner of the board grid, press ENTER.
Then move to the BOTTOM-RIGHT corner, press ENTER.
Then move to the TOP-LEFT corner of the mine counter display, press ENTER.
Then move to the BOTTOM-RIGHT corner of the mine counter display, press ENTER.
"""
import json
import os
import pyautogui
import time

CONFIG_FILE = "config.local.json"

def prompt_positive_int(prompt):
    """Prompt the user until they enter a positive integer, then return it."""
    while True:
        value = input(prompt).strip()
        try:
            n = int(value)
            if n > 0:
                return n
        except ValueError:
            pass
        print("  Invalid input — please enter a positive integer.")

def calibrate():
    input("Move mouse to TOP-LEFT corner of the board grid, then press ENTER...")
    x1, y1 = pyautogui.position()
    print(f"  Top-left: ({x1}, {y1})")

    input("Move mouse to BOTTOM-RIGHT corner of the board grid, then press ENTER...")
    x2, y2 = pyautogui.position()
    print(f"  Bottom-right: ({x2}, {y2})")

    width  = x2 - x1
    height = y2 - y1

    region = {"top": y1, "left": x1, "width": width, "height": height}

    # Auto-detect cell size (minesweeper.online uses 32px cells at default zoom)
    cell_w = width  // 30   # beginner=9, intermediate=16, expert=30
    cell_h = height // 16
    print(f"Estimated cell size: {cell_w}x{cell_h}px")

    rows = prompt_positive_int("Enter number of ROWS (e.g. 9, 16): ")
    cols = prompt_positive_int("Enter number of COLS (e.g. 9, 16, 30): ")

    # Calibrate the mine counter display region
    print("\nNow calibrate the mine counter (the red 7-segment LED display, top-left of the UI).")
    input("Move mouse to TOP-LEFT corner of the mine counter display, then press ENTER...")
    cx1, cy1 = pyautogui.position()
    print(f"  Counter top-left: ({cx1}, {cy1})")

    input("Move mouse to BOTTOM-RIGHT corner of the mine counter display, then press ENTER...")
    cx2, cy2 = pyautogui.position()
    print(f"  Counter bottom-right: ({cx2}, {cy2})")

    counter_region = {
        "top":    cy1,
        "left":   cx1,
        "width":  cx2 - cx1,
        "height": cy2 - cy1,
    }

    config = {
        "region": region,
        "rows": rows,
        "cols": cols,
        "counter_region": counter_region,
    }

    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), CONFIG_FILE)
    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4)

    print(f"\n✅ Config saved to {CONFIG_FILE}:")
    print(f'   region:         {region}')
    print(f'   rows:           {rows}')
    print(f'   cols:           {cols}')
    print(f'   counter_region: {counter_region}')

if __name__ == "__main__":
    calibrate()