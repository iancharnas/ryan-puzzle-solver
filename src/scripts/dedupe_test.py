# Currently unused but useful for debugging
import os
import os
import multiprocessing
import re
import PIL

from common import util


DUPLICATE_THRESHOLD = 8.0
SEGMENT_DIR = '2_segmented'


def dedupe_on_bmps(path):
    os.makedirs(os.path.join(path, "2a_segmented"), exist_ok=True)
    os.makedirs(os.path.join(path, "2b_thumbnails"), exist_ok=True)

    # fill_islands(input_path=os.path.join(path, SEGMENT_DIR), output_path=os.path.join(path, "2a_segmented"))
    thumbnail(input_path=os.path.join(path, "2a_segmented"), output_path=os.path.join(path, "2b_thumbnails"))
    ssd(input_path=os.path.join(path, "2b_thumbnails"))


def fill_islands(input_path, output_path):
    fs = [f for f in os.listdir(input_path) if re.match(r'.*\.bmp', f)]
    args = []
    for f in fs:
        input_img_path = os.path.join(input_path, f)
        output_img_path = os.path.join(output_path, f)
        args.append([input_img_path, output_img_path])

    with multiprocessing.Pool(processes=os.cpu_count()) as pool:
        pool.map(_fill_islands, args)


def _fill_islands(args):
    input_path, output_path = args
    pixels, width, height = util.load_bmp_as_binary_pixels(input_path)
    islands = _find_islands(pixels, ignore_islands_along_border=True, island_value=0)

    print(f"Found {len(islands)} islands in {input_path.split('/')[-1]}")
    for i, island in enumerate(islands):
        for (x, y) in island:
            pixels[y][x] = 1

    img = PIL.Image.new('1', (width, height))
    img.putdata([pixel for row in pixels for pixel in row])
    img.save(output_path)


def _find_islands(grid, callback=None, ignore_islands_along_border=False, island_value=1):
    """
    Given a grid of 0s and 1s, finds all "islands" of 1s:
    00000000
    01110000
    01111000
    00111110
    00000000

    :param grid: a 2D array of 0s and 1s
    :param callback: a function that will be called with each island found
    :param ignore_islands_along_border: if True, islands that touch the border of the grid will be ignored
    :param island_value: the value that represents an island in the grid (1 or 0)

    Returns either a list of islands, or a list of Trues if a callback was provided
    """
    visited1 = set()
    visited2 = set()
    islands = []
    for i in range(len(grid)):
        for j in range(len(grid[i])):
            if grid[i][j] == island_value and (i, j) not in visited1 and (i, j) not in visited2:
                island = set()
                queue = [(i, j)]
                touched_border = False

                # to prevent memory from getting too big and lookups from taking too long,
                # we maintain two visited sets, we check if we've visited a
                # location by checking either, and drain them offset
                if len(islands) % 160 == 0:
                    visited1 = set()
                if len(islands) % 160 == 80:
                    visited2 = set()
                while queue:
                    x, y = queue.pop(0)
                    if (x, y) not in visited1 and (x, y) not in visited2:
                        visited1.add((x, y))
                        visited2.add((x, y))
                        island.add((y, x))
                        for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                            if 0 <= x + dx < len(grid) and 0 <= y + dy < len(grid[0]) and grid[x + dx][y + dy] == island_value:
                                queue.append((x + dx, y + dy))
                        if x == 0 or y == 0 or x == len(grid) - 1 or y == len(grid[0]) - 1:
                            touched_border = True

                if ignore_islands_along_border and touched_border:
                    continue

                if callback:
                    ok = callback(island, len(islands))
                    if ok:
                        islands.append(True)
                else:
                    islands.append(island)
    return islands


def thumbnail(input_path, output_path):
    print("Creating thumbnails...")
    fs = [f for f in os.listdir(input_path) if re.match(r'.*\.bmp', f)]
    args = []
    for f in fs:
        # load the image and save off a thumbnail version scaled down to 20% then padded to 60x60
        input_img_path = os.path.join(input_path, f)
        output_img_path = os.path.join(output_path, f)
        args.append([input_img_path, output_img_path])

    with multiprocessing.Pool(processes=os.cpu_count()) as pool:
        pool.map(_thumbnail, args)


def _thumbnail(args):
    input_path, output_path = args
    img = PIL.Image.open(input_path)
    w, h = img.size[0] // 5, img.size[1] // 5
    img.thumbnail((w, h), PIL.Image.NEAREST)
    img = img.convert('1')

    # Calculate the padding size
    padding_width = (140 - img.size[0]) // 2
    padding_height = (140 - img.size[1]) // 2

    # Create a new image with the desired size and paste the thumbnail in the center
    padded_img = PIL.Image.new('1', (140, 140))
    padded_img.paste(img, (padding_width, padding_height))
    padded_img.save(output_path)


def ssd(input_path):
    print("Running SSD between all thumbnails...")
    fs = [os.path.join(input_path, f) for f in os.listdir(input_path) if re.match(r'.*\.bmp', f)]
    images = [util.load_bmp_as_binary_pixels(f)[0] for f in fs]

    dupes = set()
    keeps = set()
    debug = []

    for i, img in enumerate(images):
        if i in dupes:
            continue

        for j, other_img in enumerate(images):
            if i == j:
                continue
            ssd_score = util.normalized_ssd(img, other_img)
            fi = fs[i].split('/')[-1].split('.')[0]
            fj = fs[j].split('/')[-1].split('.')[0]
            if ssd_score < DUPLICATE_THRESHOLD:
                dupes.add(j)
                debug.append((fi, fj, ssd_score))

        keeps.add(i)

    print(f"Starting with {len(images)} images")
    print(f"Removing {len(dupes)} images")
    print(f"Resulting in {len(keeps)} images")
    debug = sorted(debug, key=lambda x: x[2])
    for i, j, s in debug:
        print(f"> Duplicate @ {s}: \t {i}.bmp {j}.bmp")


if __name__ == '__main__':
    dedupe_on_bmps(path='data')