#!/usr/local/bin/python3
"""Converts charrom.bin to charrom.png"""

from numpy import fromfile
from numpy import uint8
from numpy import unpackbits
from numpy import zeros
from numpy import stack
from PIL import Image
from time import time

if __name__ == "__main__":
    # The charrom is organized with two banks of 256 characters each (512 chars total).
    # On the C-64 only one bank is selected at a time.  We convert all 512 chars total.
    # Each character is represented as 8 bytes (one byte per row) starting at the top
    # of the character.  The most significant bit is the left most pixel.

    INFILENAME = "charrom.bin"
    OUTFILENAME = "charrom.png"
    CHARS = 512
    CHAR_SIZE = 8
    COLUMNS = 32
    ROWS = int(CHARS / COLUMNS)

    def fast_method():
        rawbytes = fromfile(INFILENAME, dtype=uint8)
        out = zeros([ROWS * CHAR_SIZE, COLUMNS * CHAR_SIZE], dtype=uint8)
        for c1 in range(ROWS):
            y = c1 * CHAR_SIZE
            _y = y * COLUMNS
            for c2 in range(COLUMNS):
                x = c2 * CHAR_SIZE
                # Convert 8 bytes to 8x8 bitmap and write to output array
                bitmap = unpackbits(rawbytes[x + _y : x + 8 + _y])
                out[y : y + 8, x : x + 8] = bitmap.reshape(8, 8)
        # Convert from depth of 1 to 4
        return Image.fromarray(stack((out * 255,) * 4, axis=-1))

    def slow_method():
        next = 0
        rawbytes = fromfile(INFILENAME, dtype=uint8)
        out = zeros([ROWS * CHAR_SIZE, COLUMNS * CHAR_SIZE, 4], dtype=uint8)
        for c1 in range(ROWS):
            for c2 in range(COLUMNS):
                y1 = c1 * CHAR_SIZE
                x1 = c2 * CHAR_SIZE
                for y2 in range(CHAR_SIZE):
                    bits = unpackbits(rawbytes[next])
                    next += 1
                    for x2 in range(CHAR_SIZE):
                        val = bits[x2]
                        if val == 1:
                            # pixel on, else transparent
                            out[y1 + y2, x1 + x2] = [255, 255, 255, 255]

        return Image.fromarray(out)

    def long_time(func, i=100):
        start = time()
        for _ in range(i):
            func()
        return time() - start

    fast = long_time(fast_method)
    slow = long_time(slow_method)
    print(f"Slow took {slow}, Fast took {fast}, Fast is {slow/fast} times as quick")
    slow_method().save(OUTFILENAME.replace(".", "_slow."))
    fast_method().save(OUTFILENAME.replace(".", "_fast."))
