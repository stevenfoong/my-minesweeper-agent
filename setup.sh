# 1. Install dependencies
pip install mss pillow opencv-python pyautogui numpy

# 2. Run calibration to find your board region
python calibrate.py

# 3. Update REGION, ROWS, COLS in main.py

# 4. Open minesweeper.online in browser, start a NEW game
#    Set zoom to 100% (Ctrl+0) for consistent cell sizes

# 5. Run the bot!
python main.py