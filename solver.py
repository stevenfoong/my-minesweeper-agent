"""
Minesweeper constraint-based solver.

Phase 1: Basic rules
  - If a numbered cell has exactly N unknown neighbours and N remaining mines → all are mines
  - If a numbered cell has 0 remaining mines → all unknown neighbours are safe

Phase 2: Subset constraint
  - If constraint A is a strict subset of constraint B, the difference cells
    have (mines_B - mines_A) mines among them, enabling further deductions.
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

def build_constraints(board):
    """
    Build a list of (unknown_neighbor_set, remaining_mine_count) constraints
    from all numbered cells on the board.
    """
    rows, cols = len(board), len(board[0])
    constraints = []

    for r in range(rows):
        for c in range(cols):
            val = board[r][c]
            if val <= 0:
                continue
            neighbors   = get_neighbors(r, c, rows, cols)
            unknowns    = frozenset(n for n in neighbors if board[n[0]][n[1]] == UNKNOWN)
            flagged_cnt = sum(1 for n in neighbors if board[n[0]][n[1]] == FLAGGED)
            remaining   = val - flagged_cnt

            if remaining < 0:
                continue  # board parse error
            if unknowns:
                constraints.append((unknowns, remaining))

    return constraints

def solve(board):
    """
    Returns:
      safe_cells  : set of (r,c) — guaranteed safe to click
      mine_cells  : set of (r,c) — guaranteed mines, flag them
      ambiguous   : list of (r,c) — cannot determine, ask user
    """
    rows, cols = len(board), len(board[0])
    safe_cells = set()
    mine_cells = set()

    constraints = build_constraints(board)
    changed = True

    while changed:
        changed = False
        new_constraints = []

        for cells, mine_count in constraints:
            # Remove already-decided cells from this constraint
            cells = cells - mine_cells - safe_cells
            mine_count -= sum(
                1 for c in list(mine_cells)
                if c in cells  # already subtracted above but safety check
            )
            # Recompute after removing known mines
            flagged_in_set = 0
            clean_cells = frozenset(
                c for c in cells if board[c[0]][c[1]] == UNKNOWN
            )

            # Basic rules
            if mine_count == 0 and clean_cells:
                safe_cells.update(clean_cells)
                changed = True
                continue
            if mine_count == len(clean_cells) and clean_cells:
                mine_cells.update(clean_cells)
                changed = True
                continue

            new_constraints.append((clean_cells, mine_count))

        # Subset rule: if A ⊂ B, then B-A has (mines_B - mines_A) mines
        for i, (cells_a, mines_a) in enumerate(new_constraints):
            for j, (cells_b, mines_b) in enumerate(new_constraints):
                if i == j or not cells_a or not cells_b:
                    continue
                if cells_a < cells_b:          # A is strict subset of B
                    diff       = cells_b - cells_a
                    diff_mines = mines_b - mines_a
                    if diff_mines == 0:
                        safe_cells.update(diff)
                        changed = True
                    elif diff_mines == len(diff):
                        mine_cells.update(diff)
                        changed = True

        constraints = new_constraints

    # Collect all unknown cells
    all_unknowns = {
        (r, c)
        for r in range(rows)
        for c in range(cols)
        if board[r][c] == UNKNOWN
    }

    decided   = safe_cells | mine_cells
    ambiguous = list(all_unknowns - decided)

    return safe_cells, mine_cells, ambiguous