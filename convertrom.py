#!/usr/local/bin/python3
"""Converts charrom.bin to charrom.png"""

from os.path import abspath
from numpy import fromfile
from numpy import uint8
from numpy import unpackbits
from numpy import zeros
from numpy import stack
from PIL import Image

#Charrom constants
CHARS = 512
CHAR_SIZE = 8
COLUMNS = 32
ROWS = CHARS // COLUMNS

def convert_rom(infile, outfile=None, get_channels=False):
    """
    Converts a charrom.bin to charrom.png (or other PIL compatible image typ)
    Set outfile to None to prevent saving and just return PIL image(s)
    Will return a PIL image (or images also including the A and B channels on their own)
    """
    #The charrom is organized with two banks of 256 characters each (512 chars total).
    #On the C-64 only one bank is selected at a time.  We convert all 512 chars total.
    #Each character is represented as 8 bytes (one byte per row) starting at the top
    #of the character.  The most significant bit is the left most pixel.
    
    rawbytes = fromfile(infile, dtype=uint8)
    out = zeros([ROWS * CHAR_SIZE, COLUMNS * CHAR_SIZE], dtype=uint8)
    for row in range(ROWS):
        y = row * CHAR_SIZE
        row_offset = y * COLUMNS
        for column in range(COLUMNS):
            x = column * CHAR_SIZE
            # Convert 8 bytes to 8x8 bitmap and write to output array
            bitmap = unpackbits(rawbytes[x + row_offset : x + 8 + row_offset]).reshape(8, 8)
            out[y : y + 8, x : x + 8] = bitmap
            # print(bitmap) # Uncomment to see each char in bitmap form
    # Convert from depth of 1 to 4 then convert array to image.
    image = Image.fromarray(stack((out * 255,) * 4, axis=-1))
    if outfile:
        image.save(outfile)
    if get_channels:
        #Calc column/row offset lengths
        quarter = int(ROWS * CHAR_SIZE / 4)
        #Get A Channel
        out_a = zeros([2*quarter, COLUMNS * CHAR_SIZE], dtype=uint8)
        out_a[:quarter,:]=out[:quarter,:]
        out_a[quarter:,:]=out[2*quarter:3*quarter,:]
        image_a = Image.fromarray(stack((out_a * 255,) * 4, axis=-1))
        #Get B Channel
        out_b = zeros([2*quarter, COLUMNS * CHAR_SIZE], dtype=uint8)
        out_b[:quarter,:]=out[quarter:2*quarter,:]
        out_b[quarter:,:]=out[3*quarter:,:]
        image_b = Image.fromarray(stack((out_b * 255,) * 4, axis=-1))
        return [image, image_a, image_b]
    else:
        return image

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Tool to convert Commodore 64 charrom.bin files to an RGBA character map.")
    parser.add_argument('infile', type=str, help="Source char rom file.")
    parser.add_argument('outfile', type=str, help = "Output file name, this is automatically modified to include _a or _b automatically when outputting A/B channels, eg. outfile.png -> outfile_a.png | Supported output file types: BMP, GIF, ICO, JPEG, PNG, and more.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("-a", action='store_true', help = "Only output A channel")
    group.add_argument('-b', action='store_true', help = "Only output B channel")
    group.add_argument("-c", action='store_true', help = "Output A, B and Composite (Normal)")
    args = parser.parse_args()
    infile, outfile = abspath(args.infile), abspath(args.outfile)
    print(f"Converting {infile}")
    if any((args.a, args.b, args.c)):
        prefix, suffix = outfile.rsplit('.', 1)
        img, img_a, img_b = convert_rom(infile, None, get_channels=True)
        if args.a or args.c:
            img_a.save(prefix+"_a."+suffix)
        if args.b or args.c:
            img_b.save(prefix+"_b."+suffix)
        if args.c:
            img.save(outfile)
    else:
        convert_rom(infile, outfile)
