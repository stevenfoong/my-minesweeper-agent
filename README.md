# 🎮 My Minesweeper Agent

A Python bot that plays Minesweeper on [minesweeper.online](https://minesweeper.online/) using constraint-based logic solving. When the logic engine cannot determine a safe move, it asks the human player to decide.

## License

This project is licensed under the **GNU General Public License v3.0 (GPL-3.0)**.  
Any modification or derivative work must also be released under GPL-3.0.

---

## Features

- 🧠 **Logic-based solver** — uses constraint propagation and subset rules
- 🚩 **Auto-flagging** — flags confirmed mines automatically
- ✅ **Auto-revealing** — clicks confirmed safe cells automatically
- ❓ **Human fallback** — asks you to decide when logic is insufficient
- 🖥️ **Screen capture** — reads the board directly from your browser
- 🖱️ **Mouse control** — clicks and right-clicks via pyautogui

---

## Project Structure

```
my-minesweeper-agent/
├── main.py           ← Main loop: capture → parse → solve → act
├── capture.py        ← Screen capture using mss
├── board_parser.py   ← Image recognition to read board state
├── solver.py         ← Constraint-based logic solver
├── controller.py     ← Mouse click/flag controller
├── calibrate.py      ← Tool to find your board's screen region
└── requirements.txt  ← Python dependencies
```

---

## 🪟 Windows Setup Guide

Follow these steps to get everything installed and running on Windows.

### Step 1 — Install Python

1. Go to the official Python download page:  
   👉 **https://www.python.org/downloads/windows/**

2. Click **"Download Python 3.x.x"** (latest stable version).

3. Run the installer (`.exe` file). On the first screen, **tick the checkbox**:  
   ☑️ **"Add Python to PATH"** ← This is important!

4. Click **"Install Now"** and wait for it to finish.

5. Verify the installation — open **Command Prompt** (`Win + R`, type `cmd`, press Enter) and run:
   ```cmd
   python --version
   ```
   You should see something like `Python 3.12.x`.

---

### Step 2 — Install Git (to download this project)

1. Go to 👉 **https://git-scm.com/download/win**
2. Download and run the installer, accepting all defaults.
3. Verify:
   ```cmd
   git --version
   ```

---

### Step 3 — Download This Project

Open **Command Prompt** and run:

```cmd
git clone https://github.com/stevenfoong/my-minesweeper-agent.git
cd my-minesweeper-agent
```

---

### Step 4 — Install Python Dependencies

Inside the project folder, run:

```cmd
pip install -r requirements.txt
```

This installs: `mss`, `pillow`, `opencv-python`, `pyautogui`, `numpy`.

> ⚠️ If you get an error like `pip not found`, try `python -m pip install -r requirements.txt` instead.

---

### Step 5 — Calibrate Your Board Region

1. Open **[minesweeper.online](https://minesweeper.online/)** in your browser.
2. Set browser zoom to **100%** by pressing `Ctrl + 0`.
3. Start a **new game**.
4. In Command Prompt, run:
   ```cmd
   python calibrate.py
   ```
5. Follow the prompts — hover your mouse over the **top-left corner** of the board grid and press Enter, then hover over the **bottom-right corner** and press Enter.
6. The script will print a `REGION` value. **Copy it**.

---

### Step 6 — Configure the Bot

Open `main.py` in Notepad or any text editor:

```cmd
notepad main.py
```

Update these two settings near the top of the file:

```python
REGION = {"top": ???, "left": ???, "width": ???, "height": ???}  # ← paste from calibrate.py
ROWS, COLS = 16, 30  # ← change to match your difficulty
```

| Difficulty   | ROWS | COLS | Mines |
|--------------|------|------|-------|
| Beginner     | 9    | 9    | 10    |
| Intermediate | 16   | 16   | 40    |
| Expert       | 16   | 30   | 99    |

Save the file (`Ctrl + S`).

---

### Step 7 — Launch the Agent! 🚀

1. In your browser, open [minesweeper.online](https://minesweeper.online/) and start a **new game**.
2. In Command Prompt, run:
   ```cmd
   python main.py
   ```
3. You have **3 seconds** to click on your browser window — the bot will then start playing!

---

### 🛑 How to Stop the Bot

- Press `Ctrl + C` in Command Prompt at any time to stop.
- Or type `quit` when the bot asks you for a manual decision.

---

## Tips for Windows

| Tip | Detail |
|-----|--------|
| **Browser zoom** | Set to **100%** (`Ctrl + 0`) — cell sizes change with zoom |
| **Display scaling** | If on a high-DPI monitor (e.g. 125% or 150% Windows scaling), go to **Display Settings → Scale** and set to **100%** while using the bot |
| **Run as normal user** | No admin rights needed |
| **Start with Beginner** | Test the bot on 9×9 before scaling up to Expert |
| **Debug mode** | Set `DEBUG = True` in `main.py` to print board state each scan |
| **Color tuning** | If the parser misreads cells, save `debug_board.png` and inspect pixel colors |

---

## How the Solver Works

```
Screen Capture → Parse Board → Apply Logic → Click/Flag → Repeat
                                    ↓
                            (if ambiguous)
                        Ask User for Decision
```

### Phase 1 — Basic Rules
- If a numbered cell's remaining mine count equals its unknown neighbour count → all unknowns are mines
- If a numbered cell's remaining mine count is 0 → all unknown neighbours are safe

### Phase 2 — Subset Constraint
- If constraint A is a strict subset of constraint B, the difference cells have `(mines_B - mines_A)` mines, enabling further deductions

---

## Contributing

Pull requests are welcome! Please ensure any modifications are also released under **GPL-3.0**.