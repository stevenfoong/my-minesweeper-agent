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

## Quick Start

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Calibrate your board region

```bash
python calibrate.py
```

Follow the prompts — move your mouse to the top-left and bottom-right corners of the board grid. Copy the output `REGION` value into `main.py`.

### 3. Configure difficulty

In `main.py`, set `ROWS` and `COLS` to match your chosen difficulty:

| Difficulty   | Rows | Cols | Mines |
|--------------|------|------|-------|
| Beginner     | 9    | 9    | 10    |
| Intermediate | 16   | 16   | 40    |
| Expert       | 16   | 30   | 99    |

### 4. Run the bot

Open [minesweeper.online](https://minesweeper.online/) in your browser, start a **new game**, then run:

```bash
python main.py
```

You have **3 seconds** to switch to your browser window!

---

## Tips

| Tip | Detail |
|-----|--------|
| **Browser zoom** | Set to **100%** (Ctrl+0) — cell sizes change with zoom |
| **Start with Beginner** | Test the bot on 9×9 before scaling up |
| **Debug mode** | Set `DEBUG = True` in `main.py` to print board state each scan |
| **HiDPI / Retina screens** | On Mac Retina or Windows >100% scaling, divide pixel coords by 2 |
| **Color tuning** | If the parser misreads cells, save `debug_board.png` and sample pixel colors |

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
