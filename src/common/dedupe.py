import os
import json
import numpy as np
import math
from glob import glob
import shutil
from pathlib import Path

from common import util, sides
from common.config import *


DOUBLE_CHECK_GEOMETRIC_DUPLICATE_THRESHOLD = 2.2
SIDE_MISALIGNMENT_RAD = 12.0 * math.pi / 180


def deduplicate(batch_data_path, input_path, output_path):
    """
    Removes duplicate vector pieces by only copying over unique pieces to the output directory
    Algorithm finds pieces whose centroids are in the same physical space (using "motor space")
    and then compares the geometry of the pieces as a double-check / a way to flag that computer vision problems might have occurred
    """
    # open up all the pieces
    print(f"Loading piece data from {input_path}...")
    pieces = {}
    piece_photo_locations = {}
    input_path = Path(input_path)
    for path in input_path.glob("side_*_0.json"):
        i = int(path.parts[-1].split('_')[1])
        piece = []
        for j in range(4):
            json_path = input_path.joinpath(f'side_{i}_{j}.json')
            with open(json_path) as f:
                data = json.load(f)
                side = sides.Side(i, j, data['vertices'], piece_center=data['piece_center'],
                                  is_edge=data['is_edge'], resample=True, rotate=False,
                                  photo_filename=data['original_photo_name'])
                piece.append(side)

                # we'll also want to know where in the photo frame this piece was
                piece_photo_locations[i] = {
                    'photo_width': data['photo_width'],
                    'photo_height': data['photo_height'],
                    # we use centroids because they are generally quite stable between different photos of identical pieces
                    'photo_space_centroid': data['photo_space_centroid'],
                }
        pieces[i] = piece

    # open the metadata that tells us where each piece was photographed
    with open(batch_data_path) as f:
        batch_data_d = json.load(f)["photos"]
    batch_data = {}
    for d in batch_data_d:
        batch_data[d["file_name"]] = d["position"]

    uniques = set()
    dupes = set()

    def _photo_space_to_robot_space(robot_space_camera_position, photo_space_position):
        return (robot_space_camera_position[0] + (photo_space_position[0] * APPROX_ROBOT_COUNTS_PER_PIXEL),
                robot_space_camera_position[1] - (photo_space_position[1] * APPROX_ROBOT_COUNTS_PER_PIXEL))

    for i, sides0 in pieces.items():
        # if this piece is duplicating someone else, skip it
        if i in dupes:
            continue

        dupes_of_i = {}
        piece_i_photo_filename = sides0[0].photo_filename
        piece_i_robot_space_camera_position = batch_data[piece_i_photo_filename]
        piece_i_motor_space_centroid = _photo_space_to_robot_space(piece_i_robot_space_camera_position, piece_photo_locations[i]['photo_space_centroid'])

        for j, sides1 in pieces.items():
            if i == j or j in dupes:
                continue

            # duplicates are pieces in the same physical location
            piece_j_photo_filename = sides1[0].photo_filename
            piece_j_robot_space_camera_position = batch_data[piece_j_photo_filename]
            piece_j_motor_space_centroid = _photo_space_to_robot_space(piece_j_robot_space_camera_position, piece_photo_locations[j]['photo_space_centroid'])

            motor_space_centroid_distance = util.distance(piece_i_motor_space_centroid, piece_j_motor_space_centroid)
            pixel_distance = motor_space_centroid_distance / APPROX_ROBOT_COUNTS_PER_PIXEL
            if pixel_distance < DUPLICATE_CENTROID_DELTA_PX:
                print(f"[{i}]\t is duplicated by {j} \t Centroid distance: {pixel_distance}")
                dupes_of_i[j] = piece_photo_locations[j]

                # just for fun, let's compare geometries
                score = _compare(sides0, sides1)
                if score > DOUBLE_CHECK_GEOMETRIC_DUPLICATE_THRESHOLD:
                    print(f"[{i}]\t is in the same position as {j} but they don't seem to match. This is usually a problem... \t Geometric Similarity: {score}")
            elif pixel_distance < 3 * DUPLICATE_CENTROID_DELTA_PX:
                print(f"\t\t\t[{i}]\t is similar to {j} \t Centroid distance: {pixel_distance}")

        if len(dupes_of_i) == 0:
            # if this piece was truly unique, keep it
            uniques.add(i)
        else:
            # if this piece has duplciates, of all the duplicates, find the "best" one
            dupes_of_i[i] = piece_photo_locations[i]
            best_dupe_id = _pick_best_dupe(dupes_of_i)
            uniques.add(best_dupe_id)
            for j, _ in dupes_of_i.items():
                if j != best_dupe_id:
                    dupes.add(j)

    print(f"Started with {len(pieces)}; found {len(dupes)} duplicate pieces; resulting in {len(uniques)} unique pieces.")

    # finally, copy all the uniques to the output directory
    for id in uniques:
        # copy the json files
        for i in range(4):
            side_i = f'side_{id}_{i}.json'
            shutil.copyfile(os.path.join(input_path, side_i), os.path.join(output_path, side_i))
        # copy the vector file as well
        vector_filename = glob(f"{id}_*.svg", root_dir=input_path)[0] # Take the 0th element, there should be exactly 1
        input_vector_file = os.path.join(input_path, vector_filename)
        output_vector_file = os.path.join(output_path, vector_filename)
        shutil.copyfile(input_vector_file, output_vector_file)

    return len(uniques)


def _pick_best_dupe(pieces):
    """
    Given a dict of piece_ids :=> piece metadata dicts, pick the best one to keep
    by finding the one that was closest to the center of the photograph
    We have highest telecentricity and image quality in the center of the frame
    """
    # grab any element to get the center coordinate of any photo (half the width and height of the photo)
    any_id = next(iter(pieces))
    any_metadata = pieces[any_id]
    center = (any_metadata['photo_width']/2, any_metadata['photo_height']/2)

    # find which ID is closest to the center of the photo
    best_id = None
    best_score = 1000000
    for id, metadata in pieces.items():
        piece_center = metadata['photo_space_centroid']
        score = util.distance(center, piece_center)
        if score < best_score:
            best_id = id
            best_score = score

    return best_id


def _compare(sides0, sides1):
    """
    Compare this piece to another piece, returning a score of how similar they are
    0 = no error
    higher = more error
    Note: we cannot assume that sides0[0] is the same as sides1[0] - they might be in different indices
    """

    side00, side01, side02, side03 = sides0
    permutations = [
        [side00, side01, side02, side03],
        [side01, side02, side03, side00],
        [side02, side03, side00, side01],
        [side03, side00, side01, side02]
    ]

    min_cumulative_error = 1000
    for sides0 in permutations:
        # first check to see if the pieces are in approximately the same orientation
        # we expect no rotation between duplicates
        sides_aligned = True
        for i in range(4):
            angle_diff = util.compare_angles(sides0[i].angle, sides1[i].angle)
            if angle_diff > SIDE_MISALIGNMENT_RAD:
                sides_aligned = False
                break
        if not sides_aligned:
            continue

        # if the sides are in approximately the same orientation, see how close to perfect matches they are
        cumulative_error = 0
        for i in range(4):
            cumulative_error += sides0[i].error_when_fit_with(sides1[i], flip=False, skip_edges=False, render=False)

        if cumulative_error < min_cumulative_error:
            min_cumulative_error = cumulative_error

    return min_cumulative_error