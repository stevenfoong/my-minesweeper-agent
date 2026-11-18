# Minesweeper Online Helper Overlay

A browser overlay for [minesweeper.online](https://minesweeper.online). It analyses the board while you play. It shows which cells are safe to open, which are certain mines, and the chance of a mine in every other closed cell.

By default it only reads the page and draws on top of it. You can optionally enable **Auto Play** to make moves using the solver.

| Mark on a cell | Meaning |
|---|---|
| Green **✓** | 100% safe, you can open it |
| Red **✖** | Certain mine, you can flag it |
| Number with a green→red tint | Chance (in %) that this cell is a mine |
| Blue outline | The safest guess. Shown only when no cell is 100% safe |
| *Italic* number | Estimate only (the area was too large to solve exactly) |

A small panel in the top-right corner of the page shows:
- how many safe cells and certain mines there are
- how risky the best guess is, when you have to guess
- warnings, for example when your flags don't match the numbers

The panel has buttons to turn the overlay or the percentages on and off, plus a **Games to play** input, separate **Start Auto Play** and **Stop** buttons, and **Guesses: on/off**. **Alt+H** also turns the overlay on and off. Your choices are remembered. The overlay hides when the game is over.

## Installation

Choose **one** of the three options.

### Option 1: Userscript (recommended, starts by itself)

1. Install a userscript extension:
   - [Tampermonkey](https://www.tampermonkey.net/) (Chrome, Edge, Firefox, Safari), or
   - [Violentmonkey](https://violentmonkey.github.io/) (Chrome, Edge, Firefox).
2. **Chrome and Edge only:** allow the extension to run user scripts:
   1. Open `chrome://extensions` (or `edge://extensions`).
   2. Click **Details** on Tampermonkey.
   3. Turn on **Allow User Scripts**.
   4. On older browser versions this option doesn't exist. Turn on **Developer mode** (top-right corner of the extensions page) instead.

   If you skip this step, the script is installed but never runs. Tampermonkey then shows a banner asking you to enable *Allow User Scripts*.
3. Open the Tampermonkey menu and choose **Create a new script**.
4. Delete the template text, then paste the whole contents of [`minesweeper-helper.user.js`](minesweeper-helper.user.js).
5. Save with **Ctrl+S**.
6. Open or refresh minesweeper.online. The **Minesweeper helper** panel appears in the top-right corner.

### Option 2: Bookmarklet (no extension needed)

1. Create a new bookmark in your browser, with any name.
2. As its URL, paste the whole contents of [`bookmarklet.txt`](bookmarklet.txt). It's a single long line that starts with `javascript:`.
3. On the game page, click the bookmark to start the helper. Click it again to toggle the overlay.

You need to click it again after every page reload.

### Option 3: Browser console (one-off)

1. On the game page, press **F12** and open the **Console** tab.
2. Paste the contents of `minesweeper-helper.user.js` and press **Enter**. Chrome may first ask you to type `allow pasting`.

## Usage

1. Start a game and open your first cell. The overlay stays empty until at least one cell is open.
2. Open the green ✓ cells and flag the red ✖ cells.
3. When nothing is green, the blue outline marks the lowest-risk cell. It is still a gamble, so check the percentage.
4. Enter the **number of games to play** (1–999). Click **Start Auto Play**. The agent handles the current board or starts a new game if the current one has already ended.
5. It marks proven mines (multiple flags can be submitted together), opens 100%-safe tiles, and only makes a guess when no guaranteed safe opening remains. With **Guesses: on**, the guess is always the closed tile with the lowest available estimated mine probability; ties choose the first matching tile. If guesses are disabled, the run stops when it can no longer progress without risk.
6. Every tile-opening action waits until the target tile has visibly revealed and the board has stopped changing for at least 450 ms. The solver is recalculated on the changed board before another opening is allowed. Certain mine flags are allowed as a batch, but must be reflected on the board before proceeding.
7. After a game finishes, the agent waits a **random 3–10 seconds** before using the game's smiley-face New Game control. It tracks completed games, wins, and losses and stops after the requested count. A currently completed board is not counted toward the new run.
8. Click **Stop** at any time, or manually click the board to cancel. Unexpected resets, inconsistent flags, missing game controls, and unacknowledged clicks also stop Auto Play.

**Auto Play is opt-in.** The game count and guessing preference are remembered, but an active run is never restored after a reload. The script verifies a server-driven reveal by observing the resulting board DOM (it does not inspect network-level response acknowledgments). It waits up to 15 seconds for a reveal or new-game action to be reflected on the board. If the website stops accepting synthetic mouse events, Auto Play stops rather than blindly continuing.

**Your flags are treated as mines.** If you place a wrong flag, the panel shows an *inconsistent* warning. Remove the flag and the numbers recalculate.

Works with every board size (Beginner, Intermediate, Expert, Custom), the dark and light themes, and any zoom level.

## How it works

1. **Reading the board.** Four times a second, the script reads each cell's state from the page's `div.cell` elements:
   - `*_closed`: closed cell
   - `*_flag`: flagged cell
   - `*_opened *_typeN`: opened cell showing the number N
   - type 10 or higher: a mine shown after the game ends

   The total number of mines is the mine counter plus the number of flags. If the board hasn't changed since the last read, nothing is recalculated.
2. **Simple deductions.** If a number already has as many mines around it as it shows, its other closed neighbours are safe. If a number has exactly as many closed neighbours as mines still missing, they are all mines. These rules are repeated until nothing changes.
3. **Exact probabilities.** The remaining closed cells next to numbers are split into separate groups. For each group the script lists every mine layout that fits all the numbers, using backtracking.
4. **Global mine count.** Each combination of layouts across groups is weighted by how many ways the leftover mines can be placed in the closed cells that touch no number. This gives exact mine probabilities, the same result you would get by checking every possible board. Cells that touch no number all get the same probability.
5. **Drawing.** A see-through layer is placed exactly over the cells (`pointer-events: none`), so all your clicks still reach the game.

A group that needs more than 2 million search steps falls back to a simple local estimate. Those cells are shown in *italics*.

## Fair play

minesweeper.online has ranked games and leaderboards. Using an assistant or automation in ranked games is likely against the site's rules. Use this helper for practice, learning, and unranked or custom games.

## Troubleshooting

| Problem | Fix |
|---|---|
| Nothing appears after installing | Enable **Allow User Scripts** or **Developer mode** for Tampermonkey (see Option 1, step 2), then refresh the page |
| The panel shows but the board has no marks | Open at least one cell. Also check that the overlay is on (**Alt+H**) |
| "Inconsistent — check your flags" | One of your flags is wrong. Remove flags near the cell the warning names |
| Auto Play stops waiting for a reveal or a restart | Check whether minesweeper.online accepted the click or completed its update. Reopen a board and start again |
| Auto Play stops because a click was not accepted | The site may no longer accept programmatically dispatched mouse events. Use the overlay manually until the click adapter is updated |
| The site changed its layout and the helper stopped working | The cell class names may have changed. Open an issue with a screenshot |

## Files

| File | Purpose |
|---|---|
| `minesweeper-helper.user.js` | The full script: solver, board reader and overlay. Install it as a userscript or paste it into the console |
| `bookmarklet.txt` | The same script packed as a bookmarklet URL |

## License

GPL-3.0. See [LICENSE](LICENSE).
