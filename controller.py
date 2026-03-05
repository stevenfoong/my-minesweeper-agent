import pyautogui
import time

pyautogui.PAUSE = 0.15  # small delay between actions

def cell_center(r, c, region, rows, cols):
    cw = region["width"]  / cols
    ch = region["height"] / rows
    x  = region["left"] + int((c + 0.5) * cw)
    y  = region["top"]  + int((r + 0.5) * ch)
    return x, y

def reveal_cell(r, c, region, rows, cols):
    """Left-click to reveal."""
    x, y = cell_center(r, c, region, rows, cols)
    pyautogui.click(x, y, button="left")

def flag_cell(r, c, region, rows, cols):
    """Right-click to flag a mine."""
    x, y = cell_center(r, c, region, rows, cols)
    pyautogui.click(x, y, button="right")

def chord_cell(r, c, region, rows, cols):
    """Double-click (chord) on a numbered cell to auto-reveal all
    non-flagged neighbors when correct number of flags are placed."""
    x, y = cell_center(r, c, region, rows, cols)
    pyautogui.doubleClick(x, y)
