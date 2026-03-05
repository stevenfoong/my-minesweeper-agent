import time
import pyautogui
from capture      import capture_board, save_screenshot
from board_parser import parse_board, print_board
from solver       import solve
from controller   import reveal_cell, flag_cell

# ── CONFIGURATION ─────────────────────────────────────────────────────────────
# Run calibrate.py first to get these values!
# minesweeper.online difficulty settings:
#   Beginner:     9x9,  10 mines
#   Intermediate: 16x16, 40 mines
#   Expert:       16x30, 99 mines

REGION = {"top": 300, "left": 400, "width": 960, "height": 512}  # update via calibrate.py
ROWS, COLS = 16, 30   # Expert mode

LOOP_DELAY   = 0.4   # seconds between board scans
DEBUG        = True  # print board state each loop

# ──────────────────────────────────────────────────────────────────────────────
def ask_user(ambiguous: list, board) -> tuple:
    """
    When logic is exhausted, show ambiguous cells and ask human to choose.
    Returns ((r, c), is_flag)
    """
    print("\n" + "="*50)
    print("⚠️  AMBIGUOUS — Logic cannot determine safe move.")
    print(f"   {len(ambiguous)} unknown cells cannot be resolved.")
    print("\n   Top candidates (pick one to reveal or flag):")

    # Prioritise cells that are neighbours of numbered cells (more info)
    shown = ambiguous[:8]
    for i, (r, c) in enumerate(shown):
        print(f"   [{i}] Row {r+1:2d}, Col {c+1:2d}")

    print("\n   Commands:")
    print("     <number>       -> reveal that cell")
    print("     f<number>      -> flag that cell as mine")
    print("     skip           -> skip this turn (re-scan board)")
    print("     quit           -> stop the bot")

    while True:
        choice = input("\n> ").strip().lower()
        if choice == "skip":
            return None, None
        if choice == "quit":
            return "quit", None
        try:
            is_flag = choice.startswith("f")
            idx     = int(choice[1:] if is_flag else choice)
            if 0 <= idx < len(shown):
                return shown[idx], is_flag
        except ValueError:
            pass
        print("   Invalid input. Try again.")

def first_click(region, rows, cols):
    """Click center of board to start — safe opening move."""
    print("🖱️  Making first click at board center...")
    reveal_cell(rows // 2, cols // 2, region, rows, cols)
    time.sleep(0.8)

def main():
    print("🎮 Minesweeper Bot for minesweeper.online")
    print("=" * 50)
    print(f"   Board: {ROWS}x{COLS}")
    print(f"   Region: {REGION}")
    print("\n⚡ Switch to your browser now! Starting in 3 seconds...")
    time.sleep(3)

    first_click(REGION, ROWS, COLS)

    move_count  = 0
    guess_count = 0

    while True:
        # 1. Capture current board state
        img   = capture_board(REGION)
        board = parse_board(img, ROWS, COLS)

        if DEBUG:
            print(f"\n── Scan #{move_count + 1} ──")
            print_board(board)

        # 2. Run solver
        safe_cells, mine_cells, ambiguous = solve(board)

        # 3. Check win condition
        unknowns_total = sum(
            1 for r in range(ROWS) for c in range(COLS)
            if board[r][c] == -1
        )
        if unknowns_total == 0:
            print("\n🎉 Board complete!")
            break

        moved = False

        # 4. Flag all confirmed mines
        for (r, c) in mine_cells:
            print(f"🚩 Flagging mine at row {r+1}, col {c+1}")
            flag_cell(r, c, REGION, ROWS, COLS)
            moved = True

        # 5. Reveal all safe cells
        for (r, c) in safe_cells:
            print(f"✅ Revealing safe cell at row {r+1}, col {c+1}")
            reveal_cell(r, c, REGION, ROWS, COLS)
            moved = True
            move_count += 1

        # 6. If nothing to do, ask human
        if not moved:
            if not ambiguous:
                print("\n🎉 No more unknown cells — game likely finished!")
                break

            guess_count += 1
            result, is_flag = ask_user(ambiguous, board)

            if result == "quit":
                print("👋 Bot stopped by user.")
                break
            if result is None:
                time.sleep(1)
                continue

            r, c = result
            if is_flag:
                print(f"🚩 User flagging ({r+1}, {c+1})")
                flag_cell(r, c, REGION, ROWS, COLS)
            else:
                print(f"🖱️  User revealing ({r+1}, {c+1})")
                reveal_cell(r, c, REGION, ROWS, COLS)

        time.sleep(LOOP_DELAY)

    print(f"\n📊 Stats: {move_count} logical moves, {guess_count} user guesses")

if __name__ == "__main__":
    main()