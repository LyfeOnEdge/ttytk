#!/usr/local/bin/python3
"""Converts charrom.bin to charrom.png"""

from numpy import fromfile
from numpy import uint8
from numpy import unpackbits
from numpy import zeros
from numpy import stack
from PIL import Image

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
    ROWS = CHARS // COLUMNS

    rawbytes = fromfile(INFILENAME, dtype=uint8)
    out = zeros([ROWS * CHAR_SIZE, COLUMNS * CHAR_SIZE], dtype=uint8)
    for c1 in range(ROWS):
        y = c1 * CHAR_SIZE
        row_offset = y * COLUMNS
        for c2 in range(COLUMNS):
            x = c2 * CHAR_SIZE
            # Convert 8 bytes to 8x8 bitmap and write to output array
            bitmap = unpackbits(rawbytes[x + row_offset : x + 8 + row_offset]).reshape(8, 8)
            # print(bitmap) # Uncomment to see chars in bitmap form
            out[y : y + 8, x : x + 8] = bitmap
    # Convert from depth of 1 to 4 then convert array to image.
    image = Image.fromarray(stack((out * 255,) * 4, axis=-1))
    image.save(OUTFILENAME)
