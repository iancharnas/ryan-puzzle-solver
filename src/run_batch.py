#!/usr/bin/env python3
"""
Entrypoint from the command line to find a puzzle solution from a batch of input photos
"""

import cProfile
import argparse
import posixpath
import os
import time
import json

import process, solve
from common import util
from common.config import *


def _prepare_new_run(path, start_at_step, stop_before_step):
    for i, d in enumerate([PHOTOS_DIR, PHOTO_BMP_DIR, SEGMENT_DIR, DEDUPED_DIR, VECTOR_DIR, CONNECTIVITY_DIR, SOLUTION_DIR, TIGHTNESS_DIR]):
        os.makedirs(os.path.join(path, d), exist_ok=True)

        if os.path.exists(os.path.join(path, d, '.DS_Store')):
            os.remove(os.path.join(path, d, '.DS_Store'))

        # wipe any directories we'll act on, except 0 which is the input
        if i != 0 and i > start_at_step and i <= stop_before_step:
            for f in os.listdir(os.path.join(path, d)):
                os.remove(os.path.join(path, d, f))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--path', required=True, help='Path to the base directory that has a dir `0_photos` full of JPEGs in it', type=str)
    parser.add_argument('--only-process-id', default=None, required=False, help='Only processes the provided ID', type=str)
    parser.add_argument('--start-at-step', default=0, required=False, help='Start processing at this step', type=int)
    parser.add_argument('--stop-before-step', default=10, required=False, help='Stop processing at this step', type=int)
    parser.add_argument('--serialize', default=False, action="store_true", help='Single-thread processing')
    args = parser.parse_args()

    start_time = time.time()

    _prepare_new_run(path=args.path, start_at_step=args.start_at_step, stop_before_step=args.stop_before_step)

    # Open the batch.json file containing the robot position each photo was taken at
    batch_info_file = posixpath.join(args.path, PHOTOS_DIR, "batch.json")
    with open(batch_info_file, "r") as jsonfile:
        batch_info = json.load(jsonfile)["photos"]
    robot_states = {}
    for d in batch_info:
        robot_states[d["file_name"]] = d["position"]

    process.batch_process_photos(path=args.path, serialize=args.serialize, robot_states=robot_states, id=args.only_process_id, start_at_step=args.start_at_step, stop_before_step=args.stop_before_step)
    if args.stop_before_step is not None and args.stop_before_step >= 3 and args.only_process_id is None:
        solve.solve(path=args.path, start_at=args.start_at_step)

    duration = time.time() - start_time
    print(f"\n\n{util.GREEN}### Ran in {round(duration, 2)} sec ###{util.WHITE}\n")


if __name__ == '__main__':
    PROFILE = False
    if PROFILE:
        cProfile.run('main()', 'profile_results.prof')
    else:
        main()
