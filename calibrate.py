"""
Run this first to find the exact screen region of your minesweeper board.
Move your mouse to the TOP-LEFT corner of the board grid, press ENTER.
Then move to the BOTTOM-RIGHT corner, press ENTER.
"""
import pyautogui
import time

def calibrate():
    input("Move mouse to TOP-LEFT corner of the board grid, then press ENTER...")
    x1, y1 = pyautogui.position()
    print(f"  Top-left: ({x1}, {y1})")

    input("Move mouse to BOTTOM-RIGHT corner of the board grid, then press ENTER...")
    x2, y2 = pyautogui.position()
    print(f"  Bottom-right: ({x2}, {y2})")

    width  = x2 - x1
    height = y2 - y1

    print("\n✅ Copy this into main.py:")
    print(f'REGION = {{"top": {{y1}}, "left": {{x1}}, "width": {{width}}, "height": {{height}}}}')

    # Auto-detect cell size (minesweeper.online uses 32px cells at default zoom)
    cell_w = width  // 30   # beginner=9, intermediate=16, expert=30
    cell_h = height // 16
    print(f"Estimated cell size: {{cell_w}}x{{cell_h}}px")

if __name__ == "__main__":
    calibrate()