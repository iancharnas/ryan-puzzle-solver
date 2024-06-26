"""
Given a path to processed piece data, finds a solution
"""

import os
import time

from common import board, connect, util, move, spacing
from common.config import *


def solve(path, start_at=3):
    """
    Given a path to processed piece data, finds a solution
    """
    if start_at <= 5:
        connectivity = _find_connectivity(input_path=os.path.join(path, DEDUPED_DIR), output_path=os.path.join(path, CONNECTIVITY_DIR))
    else:
        connectivity = None

    if start_at <= 6:
        puzzle = _build_board(connectivity=connectivity, input_path=os.path.join(path, CONNECTIVITY_DIR), output_path=os.path.join(path, SOLUTION_DIR), metadata_path=os.path.join(path, VECTOR_DIR))
        move.move_pieces_into_place(puzzle, metadata_path=os.path.join(path, DEDUPED_DIR), output_path=os.path.join(path, SOLUTION_DIR))

    if start_at <= 7:
        spacing.tighten_or_relax(solution_path=os.path.join(path, SOLUTION_DIR), output_path=os.path.join(path, TIGHTNESS_DIR))


def _find_connectivity(input_path, output_path):
    """
    Opens each piece data and finds how each piece could connect to others
    """
    print(f"\n{util.RED}### 4 - Building connectivity ###{util.WHITE}\n")
    start_time = time.time()
    connectivity = connect.build(input_path, output_path)
    duration = time.time() - start_time
    print(f"Building the graph took {round(duration, 2)} seconds")
    return connectivity


def _build_board(connectivity, input_path, output_path, metadata_path):
    """
    Searches connectivity to find the solution
    """
    print(f"\n{util.RED}### 5 - Finding where each piece goes ###{util.WHITE}\n")
    start_time = time.time()
    puzzle = board.build(connectivity=connectivity, input_path=input_path, output_path=output_path)
    duration = time.time() - start_time
    print(f"Finding where each piece goes took {round(duration, 2)} seconds")
    return puzzle
