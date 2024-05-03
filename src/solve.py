"""
Given a path to processed piece data, finds a solution
"""

import os
import time
import json

from common import board, connect, dedupe, util
from common.config import *


def solve(path):
    """
    Given a path to processed piece data, finds a solution
    TODO: return a path to the solution?
    """
    _deduplicate(input_path=os.path.join(path, VECTOR_DIR), output_path=os.path.join(path, DEDUPED_DIR))
    connectivity = _find_connectivity(input_path=os.path.join(path, DEDUPED_DIR), output_path=os.path.join(path, CONNECTIVITY_DIR))
    _build_board(connectivity=connectivity, output_path=os.path.join(path, SOLUTION_DIR), metadata_path=os.path.join(path, VECTOR_DIR))


def _deduplicate(input_path, output_path):
    """
    Often times the same piece was successfully extracted from multiple photos
    We do this on vectorized pieces to ignore noise in BMPs
    """
    print(f"\n{util.RED}### 3 - Deduplicating vector pieces ###{util.WHITE}\n")
    count = dedupe.deduplicate(input_path, output_path)
    if count != PUZZLE_NUM_PIECES:
        raise Exception(f"Expected {PUZZLE_NUM_PIECES} pieces, but found {count}")


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


def _build_board(connectivity, output_path, metadata_path):
    """
    Searches connectivity to find the solution
    """
    print(f"\n{util.RED}### 5 - Build board ###{util.WHITE}\n")
    start_time = time.time()
    board.build(connectivity=connectivity, output_path=output_path)
    duration = time.time() - start_time
    print(f"Building the board took {round(duration, 2)} seconds")

    # Save off the solution for how each piece must be moved
    # TODO - this is a mock implementation!
    dest_incenters = [(555, 444)] * 1000
    dest_rotations = [0.123] * 1000
    for i in range(1, 1001):
        for j in range(4):
            metadata_input_path = os.path.join(metadata_path, f'side_{i}_{j}.json')
            solution_output_path = os.path.join(output_path, f'side_{i}_{j}.json')
            with open(metadata_input_path, 'r') as f:
                metadata = json.load(f)
                metadata['dest_photo_space_incenter'] = dest_incenters[i-1]
                metadata['dest_rotation'] = dest_rotations[i-1]
            with open(solution_output_path, 'w') as f:
                json.dump(metadata, f)

