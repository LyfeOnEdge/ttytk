#!/usr/local/bin/python3
"""Converts charrom.bin to charrom.png"""

from numpy import fromfile
from numpy import uint8
from numpy import unpackbits
from numpy import zeros
from PIL import Image

if __name__ == "__main__":
  # The charrom is organized with two banks of 256 characters each (512 chars total).
  # On the C-64 only one bank is selected at a time.  We convert all 512 chars total.
  # Each character is represented as 8 bytes (one byte per row) starting at the top
  # of the character.  The most significant bit is the left most pixel.

  INFILENAME = 'charrom.bin'
  OUTFILENAME = 'charrom.png'
  CHARS = 512
  CHAR_SIZE = 8
  COLUMNS = 32
  ROWS = int(CHARS / COLUMNS)
  out = zeros([ROWS * CHAR_SIZE, COLUMNS * CHAR_SIZE, 3], dtype=uint8)
  next = 0
  rawbytes = fromfile(INFILENAME, dtype=uint8)
  for c1 in range(ROWS):
    for c2 in range(COLUMNS):
      y1 = c1 * CHAR_SIZE
      x1 = c2 * CHAR_SIZE
      for y2 in range(CHAR_SIZE):
        bits = unpackbits(rawbytes[next])
        next+=1
        for x2 in range(CHAR_SIZE):
          val = bits[x2]
          if val == 0:
            # mark transparent, else pixel
            out[y1 + y2, x1 + x2] = [255, 255, 255]

  Image.fromarray(out).save(OUTFILENAME)
