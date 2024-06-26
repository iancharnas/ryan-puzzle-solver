import os
import re
import subprocess
import pathlib

from common.config import *


def batch_extract(input_path, output_path, scale_factor):
    # just-in-time compile the C library to find islands
    source_file = pathlib.Path(os.path.join(os.path.dirname(__file__), '../c/find_islands.c'))
    cmd = fr"gcc -pthread -O3 -march=native -funroll-loops -ffast-math -o find_islands.o '{source_file}'"
    print(cmd)
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error compiling: {e}")
        exit(1)

    # invoke the C library to find islands
    input_path = pathlib.Path(input_path)
    output_path = pathlib.Path(output_path)
    cmd = fr".{os.path.sep}find_islands.o '{input_path}' '{output_path}' {MIN_PIECE_AREA}"
    print(cmd)
    try:
        subprocess.run(cmd, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error running extract lib: {e}")
        exit(1)

    output_photo_space_positions = {}

    fs = [f for f in os.listdir(output_path) if re.match(r'.*\.bmp', f)]
    for f in fs:
        components = f.split('.')[0].split('_')
        origin_component = components[-1]
        origin_x, origin_y = origin_component.strip('(').strip(')').split(',')
        origin = (int(origin_x), int(origin_y))

        photo_space_position = (origin[0] / scale_factor + CROP_TOP_RIGHT_BOTTOM_LEFT[-1], origin[1] / scale_factor + CROP_TOP_RIGHT_BOTTOM_LEFT[0])
        output_photo_space_positions[f] = photo_space_position
        print(f"Extracted {f} at {photo_space_position}, origin {origin}")

    return output_photo_space_positions
