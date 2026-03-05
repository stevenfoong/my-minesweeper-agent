"""
Minesweeper constraint-based solver.

Phase 1: Basic rules
  - If a numbered cell has exactly N unknown neighbours and N remaining mines -> all are mines
  - If a numbered cell has 0 remaining mines -> all unknown neighbours are safe

Phase 2: Subset constraint
  - If constraint A is a strict subset of constraint B, the difference cells
    have (mines_B - mines_A) mines among them, enabling further deductions.

Phase 3: Global mine-counter constraint
  - If remaining_mines == 0 -> all unknown cells are safe (reveal them all)
  - If remaining_mines == number of unknown cells -> all unknowns are mines
"""

UNKNOWN = -1
FLAGGED = -2

def get_neighbors(r, c, rows, cols):
    return [
        (r + dr, c + dc)
        for dr in (-1, 0, 1)
        for dc in (-1, 0, 1)
        if (dr, dc) != (0, 0)
        and 0 <= r + dr < rows
        and 0 <= c + dc < cols
    ]

def build_constraints(board, known_mines=None, known_safe=None):
    """
    Build a list of (unknown_neighbor_set, remaining_mine_count) constraints
    from all numbered cells on the board, taking into account already-decided cells.
    """
    if known_mines is None:
        known_mines = set()
    if known_safe is None:
        known_safe = set()

    rows, cols = len(board), len(board[0])
    constraints = []

    for r in range(rows):
        for c in range(cols):
            val = board[r][c]
            if val <= 0:
                continue
            neighbors = get_neighbors(r, c, rows, cols)

            # Count board-flagged AND solver-identified mines
            flagged_cnt     = sum(1 for n in neighbors if board[n[0]][n[1]] == FLAGGED)
            solver_mine_cnt = sum(1 for n in neighbors if n in known_mines)
            remaining = val - flagged_cnt - solver_mine_cnt

            if remaining < 0:
                continue  # board parse error / over-flagged

            # Only include truly undecided unknown cells
            unknowns = frozenset(
                n for n in neighbors
                if board[n[0]][n[1]] == UNKNOWN
                and n not in known_mines
                and n not in known_safe
            )

            if unknowns:
                constraints.append((unknowns, remaining))

    return constraints

def solve(board, remaining_mines=None):
    """
    Returns:
      safe_cells  : set of (r,c) — guaranteed safe to click
      mine_cells  : set of (r,c) — guaranteed mines, flag them
      ambiguous   : list of (r,c) — cannot determine, ask user

    remaining_mines: int or None — the mine counter read from the UI.
      If 0, all unknowns are safe.
      If equal to number of unknowns, all unknowns are mines.
    """
    rows, cols = len(board), len(board[0])
    safe_cells = set()
    mine_cells = set()

    # Collect all unknown cells upfront
    all_unknowns = {
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if board[r][c] == UNKNOWN
    }

    # Phase 3: Global mine-counter constraint
    # Only trust the counter if it passes plausibility checks
    if remaining_mines is not None and isinstance(remaining_mines, int):
        total_cells = rows * cols
        flagged_count = sum(
            1 for r in range(rows) for c in range(cols)
            if board[r][c] == FLAGGED
        )
        n_unknowns = len(all_unknowns)

        # Basic sanity: counter must be non-negative and not exceed board size
        counter_plausible = 0 <= remaining_mines <= total_cells

        # For "remaining_mines == 0 → all safe" rule:
        # Only trust it if at least one flag has already been placed on the board.
        # This prevents false positives on early scans when counter OCR is unreliable.
        if counter_plausible and remaining_mines == 0 and flagged_count > 0:
            safe_cells.update(all_unknowns)
        # For "all unknowns are mines" rule:
        # Only trust it if remaining_mines > 0 and equals number of unknowns
        elif counter_plausible and remaining_mines > 0 and remaining_mines == n_unknowns:
            mine_cells.update(all_unknowns)

    changed = True
    while changed:
        changed = False

        # Rebuild constraints each iteration with latest known mines/safe cells
        constraints = build_constraints(board, mine_cells, safe_cells)
        new_constraints = []

        for cells, mine_count in constraints:
            # Basic rules
            if mine_count == 0 and cells:
                newly_safe = cells - safe_cells
                if newly_safe:
                    safe_cells.update(newly_safe)
                    changed = True
                continue
            if mine_count == len(cells) and cells:
                newly_mined = cells - mine_cells
                if newly_mined:
                    mine_cells.update(newly_mined)
                    changed = True
                continue

            new_constraints.append((cells, mine_count))

        # Subset rule: if A is strict subset of B, then B-A has (mines_B - mines_A) mines
        for i, (cells_a, mines_a) in enumerate(new_constraints):
            for j, (cells_b, mines_b) in enumerate(new_constraints):
                if i == j or not cells_a or not cells_b:
                    continue
                if cells_a < cells_b:   # A is strict subset of B
                    diff       = cells_b - cells_a
                    diff_mines = mines_b - mines_a
                    if diff_mines == 0:
                        newly_safe = diff - safe_cells
                        if newly_safe:
                            safe_cells.update(newly_safe)
                            changed = True
                    elif diff_mines == len(diff):
                        newly_mined = diff - mine_cells
                        if newly_mined:
                            mine_cells.update(newly_mined)
                            changed = True

    decided   = safe_cells | mine_cells
    ambiguous = list(all_unknowns - decided)

    return safe_cells, mine_cells, ambiguous
