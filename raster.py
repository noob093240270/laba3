import math
import sys
import threading


def run_with_deep_recursion(func, *args):
    result, error = [None], [None]

    def target():
        try:
            result[0] = func(*args)
        except BaseException as e:
            error[0] = e

    old_limit = sys.getrecursionlimit()
    sys.setrecursionlimit(1_000_000)
    try:
        for size_mb in (256, 64, 0):
            try:
                threading.stack_size(size_mb * 1024 * 1024)
                t = threading.Thread(target=target)
                t.start()
                break
            except (ValueError, RuntimeError, MemoryError):
                continue
        t.join()
    finally:
        threading.stack_size(0)
        sys.setrecursionlimit(old_limit)

    if error[0] is not None:
        raise error[0]
    return result[0]


def scanline_fill(image, seed, color=(0, 0, 0), pattern=None):
    w, h = image.size
    sx, sy = seed
    if not (0 <= sx < w and 0 <= sy < h):
        return 0

    px = image.load()
    target = px[sx, sy]
    visited = bytearray(w * h)

    use_pattern = pattern is not None
    if use_pattern:
        pattern = pattern.convert('RGB')
        pp = pattern.load()
        pw, ph = pattern.size
        ox, oy = pw // 2 - sx, ph // 2 - sy
    count = 0

    def fill(x, y):
        nonlocal count
        row = y * w
        if visited[row + x] or px[x, y] != target:
            return

        left = x
        while left > 0 and not visited[row + left - 1] and px[left - 1, y] == target:
            left -= 1
        right = x
        while right < w - 1 and not visited[row + right + 1] and px[right + 1, y] == target:
            right += 1

        if use_pattern:
            py = (y + oy) % ph
            for i in range(left, right + 1):
                px[i, y] = pp[(i + ox) % pw, py]
        else:
            for i in range(left, right + 1):
                px[i, y] = color
        visited[row + left: row + right + 1] = b'\x01' * (right - left + 1)
        count += right - left + 1

        for ny in (y - 1, y + 1):
            if 0 <= ny < h:
                nrow = ny * w
                for i in range(left, right + 1):
                    if not visited[nrow + i] and px[i, ny] == target:
                        fill(i, ny)

    run_with_deep_recursion(fill, sx, sy)
    return count


DIRECTIONS = [(1, 0), (1, -1), (0, -1), (-1, -1), (-1, 0), (-1, 1), (0, 1), (1, 1)]


def colors_close(c1, c2, tolerance):
    return abs(c1[0] - c2[0]) + abs(c1[1] - c2[1]) + abs(c1[2] - c2[2]) <= tolerance


def find_border_start(image, x, y, tolerance=0):
    w, h = image.size
    if not (0 <= x < w and 0 <= y < h):
        return None, None
    px = image.load()
    inner = px[x, y]
    while x + 1 < w:
        x += 1
        if not colors_close(px[x, y], inner, tolerance):
            return (x, y), px[x, y]
    return None, None


def trace_border(image, start, border_color, tolerance=0, max_steps=None):
    w, h = image.size
    px = image.load()

    def is_border(x, y):
        return 0 <= x < w and 0 <= y < h and colors_close(px[x, y], border_color, tolerance)

    if max_steps is None:
        max_steps = 8 * w * h
    path = [start]
    cur = start
    came_dir = None
    seen = {}

    for _ in range(max_steps):
        if came_dir is None:
            d0 = 5
        else:
            d0 = (came_dir - 2) % 8
        for k in range(8):
            d = (d0 + k) % 8
            nx, ny = cur[0] + DIRECTIONS[d][0], cur[1] + DIRECTIONS[d][1]
            if is_border(nx, ny):
                break
        else:
            return path

        state = (cur, d)
        if state in seen:
            return path[seen[state]:-1]
        seen[state] = len(path) - 1

        cur, came_dir = (nx, ny), d
        path.append(cur)

    return path


def bresenham_line(x0, y0, x1, y1, plot):
    dx, dy = abs(x1 - x0), abs(y1 - y0)
    sx = 1 if x1 >= x0 else -1
    sy = 1 if y1 >= y0 else -1
    x, y = x0, y0

    if dx >= dy:
        d = 2 * dy - dx
        for _ in range(dx + 1):
            plot(x, y)
            if d >= 0:
                y += sy
                d += 2 * (dy - dx)
            else:
                d += 2 * dy
            x += sx
    else:
        d = 2 * dx - dy
        for _ in range(dy + 1):
            plot(x, y)
            if d >= 0:
                x += sx
                d += 2 * (dx - dy)
            else:
                d += 2 * dx
            y += sy


def wu_line(x0, y0, x1, y1, plot):
    steep = abs(y1 - y0) > abs(x1 - x0)
    if steep:
        x0, y0, x1, y1 = y0, x0, y1, x1
    if x0 > x1:
        x0, x1, y0, y1 = x1, x0, y1, y0

    def put(x, y, c):
        if steep:
            plot(y, x, c)
        else:
            plot(x, y, c)

    dx, dy = x1 - x0, y1 - y0
    put(x0, y0, 1.0)
    if dx == 0:
        return
    put(x1, y1, 1.0)

    gradient = dy / dx
    y = y0 + gradient
    for x in range(x0 + 1, x1):
        iy = math.floor(y)
        frac = y - iy
        put(x, iy, 1.0 - frac)
        put(x, iy + 1, frac)
        y += gradient
