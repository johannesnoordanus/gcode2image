#!/usr/bin/env python3
"""
gcode2image: convert gode to image.
"""
__version__ = "v1.0.0-beta"

import sys
import re
import argparse
from PIL import Image
from skimage.draw import line as drawline
import numpy as np

import matplotlib.pyplot as plt

def gcode2image(args) -> np.array:
    """
    Convert gcode to array using header info from .gc(ode) file.
    """
    # gcode: TextIO

    # set args
    gcode = args.gcode
    G0_gray = 60 if args.showG0 else 0

    X_pattern = "X[0-9]+\.[0-9]+"
    Y_pattern = "Y[0-9]+\.[0-9]+"
    S_pattern = "S[0-9]+"

    gcode_pattern = "^(G0|G1|X|Y|M4|M3|M5|M2|S)"

    invert_intensity = True

    def pixel_intensity(S: int = None) -> int:
        # S_max (max laser power)
        # pixel intensity (inverse) proportional to laser power
        return round((1.0 - float(S/S_max)) * 255) if invert_intensity else round(float(S/S_max) * 255)

    def draw_line(X: int, Y: int, S: int = None):
        nonlocal x
        nonlocal y
        nonlocal X_start
        nonlocal Y_start
        nonlocal S_current

        if X != x or Y != y:
            if M3_mode or M4_mode:
                # draw line
                yy, xx = drawline(y - Y_start,x - X_start, Y - Y_start, X - X_start)
                if  X > x or Y > y:
                    image[yy[:-1], xx[:-1]] = pixel_intensity(S if S is not None else G0_gray)
                else:
                    image[yy[1:], xx[1:]] = pixel_intensity(S if S is not None else G0_gray)
            x = X
            y = Y

        S_current = S if S else S_current

    def get_XY(XY: str, line: str):
        return re.search(X_pattern if XY == 'X' else Y_pattern,line)

    def set_XY(XY, xy):
        return round(float(XY.group(0)[1:])/pixelsize) if XY else xy

    def get_S(line: str):
        return re.search(S_pattern,line)

    def set_S(S):
        nonlocal S_current
        return int(S.group(0)[1:]) if S else S_current

    def parse_G0(line: str):
        nonlocal G0_mode
        nonlocal G1_mode
        nonlocal S_current
        G0_mode = True
        G1_mode = False
        if 'X' in line or 'Y' in line or 'S' in line:
            # get X, Y, S
            X = get_XY('X',line)
            Y = get_XY('Y',line)
            S = get_S(line)

            # set X, Y, S
            X = set_XY(X,x)
            Y = set_XY(Y,y)
            S_current = set_S(S)

            draw_line(X, Y)

    def parse_G1(line:str):
        nonlocal G0_mode
        nonlocal G1_mode
        G0_mode = False
        G1_mode = True
        if 'X' in line or 'Y' in line or 'S' in line:
            # get X, Y, S
            X = get_XY('X',line)
            Y = get_XY('Y',line)
            S = get_S(line)

            # set X, Y, S
            X = set_XY(X,x)
            Y = set_XY(Y,y)
            S = set_S(S)

            draw_line(X, Y, S)

    def parse_XY(line):
        if G0_mode or G1_mode:
            if "X" in line or "Y" in line or "S" in line:
                # get X, Y, S
                X = get_XY('X',line)
                Y = get_XY('Y',line)
                S = get_S(line)

                # set X, Y, S
                X = set_XY(X,x)
                Y = set_XY(Y,y)
                S = set_S(S)

                draw_line(X, Y, S if G1_mode else None)

    def parse_M(line):
        nonlocal M4_mode
        nonlocal M3_mode
        nonlocal S_current
        if 'M3' in line:
            M3_mode = True
            M4_mode = False
            S = get_S(line)
            S_current = set_S(S)
        elif 'M4' in line:
            M3_mode = False
            M4_mode = True
            S = get_S(line)
            S_current = set_S(S)
        elif 'M5' in line:
            M3_mode = False
            M4_mode = False

    def parse_S(line):
        nonlocal S_current
        S = get_S(line)
        S_current = set_S(S)

    def parse_lines():
        nonlocal gcode

        while True:
            line = gcode.readline()
            if line == '':
                # exit at EOF
                break
            #print(line, end='')
            if re.search(gcode_pattern, line):
                if 'G0' in line:
                    parse_G0(line)
                elif 'G1' in line:
                    parse_G1(line)
                elif 'X' in line or 'Y' in line:
                    parse_XY(line)
                elif 'M3' in line or 'M4' in line or 'M5' in line:
                    parse_M(line)
                elif 'S' in line:
                    parse_S(line)
                elif 'M2' in line:
                    # program end: stop
                    break

    def find_min_max_X_Y_S():
        nonlocal gcode
        min_max = { 'min_X': None, 'min_Y': None, 'max_X': None, 'max_Y': None, 'max_S': None }

        while True:
            line = gcode.readline()

            if line == '':
                # exit at EOF
                break
            if re.search(gcode_pattern, line):
                X = re.search("X[0-9]+\.[0-9]+",line)
                if X:
                    X = float(X.group(0)[1:])
                    min_max['min_X'] = X if not min_max['min_X'] or X < min_max['min_X'] else min_max['min_X']
                    min_max['max_X'] = X if not min_max['max_X'] or X > min_max['max_X'] else min_max['max_X']
                Y = re.search("Y[0-9]+\.[0-9]+",line)
                if Y:
                    Y = float(Y.group(0)[1:])
                    min_max['min_Y'] = Y if not min_max['min_Y'] or Y < min_max['min_Y'] else min_max['min_Y']
                    min_max['max_Y'] = Y if not min_max['max_Y'] or Y > min_max['max_Y'] else min_max['max_Y']

                S = re.search("S[0-9]+",line)
                if S:
                    S = float(S.group(0)[1:])
                    min_max['max_S'] = S if not min_max['max_S'] or S > min_max['max_S'] else min_max['max_S']

        return min_max

    # min_max = { 'min_X': None, 'min_Y': None, 'max_X': None, 'max_Y': None, 'max_S': None }
    # first pass: find min max of coordinates and S value
    min_max = find_min_max_X_Y_S()

    # set resolution to 254 DPI (assuming 1 gcode unit is 1 mm)
    pixelsize = .1
    img_height = round(min_max['max_Y']/pixelsize)
    img_width = round(min_max['max_X']/pixelsize)
    X_start = round(min_max['min_X']/pixelsize)
    Y_start = round(min_max['min_Y']/pixelsize)

    # set max S value (calibrate)
    S_max = float(min_max['max_S'])

    # show image offset
    X_start = 0 if args.offset else X_start
    Y_start = 0 if args.offset else Y_start

    # set current (x,y)
    x = X_start
    y = Y_start

    # init image
    image = np.full([img_height - Y_start + 1, img_width - X_start + 1], 255, dtype=np.uint8)

    # init modes (gcode)
    M4_mode = False
    M3_mode = False
    G0_mode = False
    G1_mode = False

    # init S value
    S_current = None

    # second pass: draw image lines
    # until EOF
    gcode.seek(0)
    parse_lines()

    return image

def main() -> int:
    """
    main
    """
    # Define command line argument interface
    parser = argparse.ArgumentParser(description='Convert a gcode file to image.')
    parser.add_argument('gcode', type=argparse.FileType('r'), default = sys.stdin, help='name of gcode file to convert')
    parser.add_argument('image', type=argparse.FileType('w'), help='image out')
    parser.add_argument('--showimage', action='store_true', default=False, help='show b&w converted image' )
    parser.add_argument('--showaxes', action='store_true', default=False, help='show image with xy-axis ' )
    parser.add_argument('--showG0', action='store_true', default=False, help='show G0 moves' )
    parser.add_argument('--offset', action='store_true', default=False, help='show image offset' )
    parser.add_argument('--flip', action='store_true', default=False, help='flip image updown' )
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__, help="show version number and exit")
    args = parser.parse_args()

    # convert to narray
    img = gcode2image(args)

    # convert to image
    if args.flip or args.showaxes:
        if not args.flip:
            print("Warning: option '--showaxes' always flips the image")
        # flip it
        img = np.flipud(img)
    pic = Image.fromarray(img)

    if args.showaxes:
        if args.showimage:
            print("Warning: option '--showaxes' overrides '--showimage'")
        r = 10

        fig, ax = plt.subplots()
        ax.imshow(img, cmap='gray', extent=(0,img.shape[1]/r,0,img.shape[0]/r) )
        ax.set_xlabel("distance [mm/pixel]")
        ax.set_ylabel("distance [mm/pixel]")

        plt.show()
    elif args.showimage:
        # show image
        pic.show()

    # write image file (png)
    #pic.save(os.path.basename(args.gcode.name).rsplit('.',1)[0] + '_gc2img.png')
    pic.save(args.image.name)

    return 0

if __name__ == '__main__':
    sys.exit(main())
