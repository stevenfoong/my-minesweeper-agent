import time
import threading
import pyautogui
import keyboard  # pip install keyboard
from capture      import capture_board, save_screenshot
from board_parser import parse_board, print_board, is_game_over
from solver       import solve
from controller   import reveal_cell, flag_cell, start_new_game

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
AUTO_RESTART = True  # automatically start a new game after win or loss

# ── STOP FLAG ─────────────────────────────────────────────────────────────────
# Shared flag — set to True when Ctrl+S is pressed to stop the bot gracefully
stop_flag = threading.Event()

def setup_hotkey():
    """
    Register Ctrl+S as a global hotkey to stop the bot.
    Runs in a background thread so it works even when the browser is in focus.
    """
    def on_stop():
        print("\n🛑 Ctrl+S detected — stopping the bot gracefully...")
        stop_flag.set()

    keyboard.add_hotkey("ctrl+s", on_stop)
    keyboard.wait()  # blocks this thread, listening for hotkeys

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
        # Also check stop_flag while waiting for user input
        if stop_flag.is_set():
            return "quit", None
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

def play_one_game():
    """
    Play a single game and return the outcome.
    Returns: "win", "loss", or "stopped"
    """
    first_click(REGION, ROWS, COLS)

    move_count  = 0
    guess_count = 0

    def _print_game_stats():
        print(f"   Stats this game: {move_count} logical moves, {guess_count} guesses")

    while not stop_flag.is_set():
        # 1. Capture current board state
        img   = capture_board(REGION)
        board = parse_board(img, ROWS, COLS)

        if DEBUG:
            print(f"\n── Scan #{move_count + 1} ──")
            print_board(board)

        # 2. Check for game-over loss (exploded mine detected)
        if is_game_over(board):
            print("\n💥 Mine hit — game over! (loss)")
            _print_game_stats()
            return "loss"

        # 3. Run solver
        safe_cells, mine_cells, ambiguous = solve(board)

        # 4. Check win condition
        unknowns_total = sum(
            1 for r in range(ROWS) for c in range(COLS)
            if board[r][c] == -1
        )
        if unknowns_total == 0:
            print("\n🎉 Board complete! (win)")
            _print_game_stats()
            return "win"

        moved = False

        # 5. Flag all confirmed mines
        for (r, c) in mine_cells:
            if stop_flag.is_set():
                break
            print(f"🚩 Flagging mine at row {r+1}, col {c+1}")
            flag_cell(r, c, REGION, ROWS, COLS)
            moved = True

        # 6. Reveal all safe cells
        for (r, c) in safe_cells:
            if stop_flag.is_set():
                break
            print(f"✅ Revealing safe cell at row {r+1}, col {c+1}")
            reveal_cell(r, c, REGION, ROWS, COLS)
            moved = True
            move_count += 1

        # 7. If nothing to do, ask human
        if not moved and not stop_flag.is_set():
            if not ambiguous:
                print("\n🎉 No more unknown cells — game likely finished!")
                _print_game_stats()
                return "win"

            guess_count += 1
            result, is_flag = ask_user(ambiguous, board)

            if result == "quit":
                print("👋 Bot stopped by user.")
                return "stopped"
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

    return "stopped"

def main():
    print("🎮 Minesweeper Bot for minesweeper.online")
    print("=" * 50)
    print(f"   Board: {ROWS}x{COLS}")
    print(f"   Region: {REGION}")
    print(f"   Auto-restart: {'ON' if AUTO_RESTART else 'OFF'}")
    print("\n   ⌨️  Press Ctrl+S at any time to stop the bot.")
    print("\n⚡ Switch to your browser now! Starting in 3 seconds...")

    # Start hotkey listener in a background daemon thread
    hotkey_thread = threading.Thread(target=setup_hotkey, daemon=True)
    hotkey_thread.start()

    time.sleep(3)

    # Check if already stopped before even starting
    if stop_flag.is_set():
        print("👋 Bot stopped before starting.")
        return

    wins   = 0
    losses = 0
    game   = 0

    while not stop_flag.is_set():
        game += 1
        print(f"\n{'='*50}")
        print(f"🎯 Starting game #{game}  (wins: {wins}  losses: {losses})")
        print(f"{'='*50}")

        outcome = play_one_game()

        if outcome == "win":
            wins += 1
        elif outcome == "loss":
            losses += 1
        elif outcome == "stopped":
            break

        if stop_flag.is_set():
            break

        if AUTO_RESTART and outcome in ("win", "loss"):
            print(f"\n🔄 Auto-restarting in 1 second…  (F2)")
            time.sleep(1)
            start_new_game()
            time.sleep(1)   # wait for the board to reset
        else:
            # AUTO_RESTART is off — stop after the first game ends
            break

    if stop_flag.is_set():
        print("\n🛑 Bot stopped via Ctrl+S.")

    print(f"\n📊 Overall stats: {game} game(s) played — {wins} win(s), {losses} loss(es)")

if __name__ == "__main__":
    main()