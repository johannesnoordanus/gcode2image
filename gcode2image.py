#!/usr/bin/env python3
"""
gcode2image: convert gcode to image.
"""
__version__ = "2.0.0"

import sys
import re
import argparse
from PIL import Image
from skimage.draw import line as drawline
import numpy as np

def gcode2image(args) -> np.array:
    """
    Convert gcode to array using header info from .gc(ode) file.
    """
    # gcode: TextIO

    # set args
    gcode = args.gcode
    G0_gray = 210 if args.showG0 else 0

    X_pattern = "X[+\-]?[0-9]+(\.[0-9]+)?"
    Y_pattern = "Y[+\-]?[0-9]+(\.[0-9]+)?"
    S_pattern = "S[0-9]+"

    gcode_pattern = "^(G0|G1|X|Y|M4|M3|M5|M2|S)"

    invert_intensity = True

    def pixel_range(ra, dY, dX, pixelsize, img_height, img_width):
        """
        Make range fit within window
        """
        dYmin = round(dY/pixelsize) if round(dY/pixelsize)-ra < 0 else round(dY/pixelsize)-ra
        dYplus = round(dY/pixelsize) if round(dY/pixelsize)+ra > img_height else round(dY/pixelsize)+ra
        dXmin = round(dX/pixelsize) if round(dX/pixelsize)-ra < 0 else round(dX/pixelsize)-ra
        dXplus = round(dX/pixelsize) if round(dX/pixelsize)+ra > img_width else round(dX/pixelsize)+ra

        return (dYmin, dYplus, dXmin, dXplus)

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
            if M3_mode or M4_mode or G0_gray:
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
                X = re.search(X_pattern,line)
                if X:
                    X = float(X.group(0)[1:])
                    min_max['min_X'] = X if not min_max['min_X'] or X < min_max['min_X'] else min_max['min_X']
                    min_max['max_X'] = X if not min_max['max_X'] or X > min_max['max_X'] else min_max['max_X']
                Y = re.search(Y_pattern,line)
                if Y:
                    Y = float(Y.group(0)[1:])
                    min_max['min_Y'] = Y if not min_max['min_Y'] or Y < min_max['min_Y'] else min_max['min_Y']
                    min_max['max_Y'] = Y if not min_max['max_Y'] or Y > min_max['max_Y'] else min_max['max_Y']

                S = re.search("S[0-9]+",line)
                if S:
                    S = float(S.group(0)[1:])
                    min_max['max_S'] = S if not min_max['max_S'] or S > min_max['max_S'] else min_max['max_S']

        return min_max

    # first pass: find min max of coordinates and S value
    min_max = find_min_max_X_Y_S()

    # set resolution to 254 DPI (assuming 1 gcode unit is 1 mm)
    pixelsize = .1

    # save image lower left
    img_min_X = min_max['min_X']
    img_min_Y = min_max['min_Y']

    if args.showOrigin:
        # set possibly new lower left upper right for image to include the origin
        min_max['min_X'] = 0 if 0 < min_max['min_X'] else min_max['min_X']
        min_max['max_X'] = 0 if 0 > min_max['max_X'] else min_max['max_X']
        min_max['min_Y'] = 0 if 0 < min_max['min_Y'] else min_max['min_Y']
        min_max['max_Y'] = 0 if 0 > min_max['max_Y'] else min_max['max_Y']

        # X/Y start is used by 'draw_line' as offset
        X_start = round(min_max['min_X']/pixelsize)
        Y_start = round(min_max['min_Y']/pixelsize)

        # set current (x,y) and correct for possibly new origin
        x = round((min_max['min_X'] + abs(min_max['min_X'] - img_min_X))/pixelsize)
        y = round((min_max['min_Y'] + abs(min_max['min_Y'] - img_min_Y))/pixelsize)
    else:
        # X/Y start is used by 'draw_line' as offset
        X_start = round(min_max['min_X']/pixelsize)
        Y_start = round(min_max['min_Y']/pixelsize)

        # set current (x,y)
        x = X_start
        y = Y_start

    # set image dimensions
    img_height = round(abs((min_max['max_Y'] - min_max['min_Y']))/pixelsize)
    img_width = round(abs((min_max['max_X'] - min_max['min_X']))/pixelsize)

    # set max S value (calibrate)
    S_max = float(min_max['max_S'])

    # init image
    image = np.full([img_height + 1, img_width + 1], 255, dtype=np.uint8)

    # show grid if requested
    if args.grid:
        # make grid
        for i in range(100,image.shape[1] if image.shape[1] >= image.shape[0] else image.shape[0],100):
            image[i:i+1,:] = 180
            image[:,i:i+1] = 180

    # show origin if requested
    if args.showOrigin:
        # calculate origin
        dX = -img_min_X if min(0.0, img_min_X) != 0.0 else 0.0
        dY = -img_min_Y if min(0.0, img_min_Y) != 0.0 else 0.0

        # get the right pixel ranges to keep within array borders
        ra8 = pixel_range(8, dY, dX, pixelsize, img_height, img_width)
        # show origin
        image[ra8[0]:ra8[1], ra8[2]:ra8[3]] = 100

        # get pixel range of X/Y-axis lines
        ra2 = pixel_range(2, dY, dX, pixelsize, img_height, img_width)

        # draw X/Y axis lines
        image[ra2[0]:ra2[1],0:img_width] = 100
        image[0:img_height,ra2[2]:ra2[3]] = 100

        # draw X-axis line markers
        for i in range(0,round(img_width/pixelsize), 10):
            #image[dYmin8:dYplus8,i] = 0
            ra = pixel_range(2, 0, i, pixelsize, img_height, img_width)
            iXmin = ra[2]
            iXplus = ra[3]
            image[ra8[0]:ra8[1],iXmin:iXplus] = 100

        # draw Y-axis line markers
        for i in range(0,round(img_height/pixelsize), 10):
            ra = pixel_range(2, i, 0, pixelsize, img_height, img_width)
            iYmin = ra[0]
            iYplus = ra[1]
            image[iYmin:iYplus,ra8[2]:ra8[3]] = 100

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
    parser.add_argument('--showG0', action='store_true', default=False, help='show G0 moves' )
    parser.add_argument('--showOrigin', action='store_true', default=False, help='show image origin (0,0)' )
    parser.add_argument('--flip', action='store_true', default=False, help='flip image updown' )
    parser.add_argument('--grid', action='store_true', default=False, help='show a grid 10mm wide' )
    parser.add_argument('-V', '--version', action='version', version='%(prog)s ' + __version__, help="show version number and exit")
    args = parser.parse_args()

    # convert to narray
    img = gcode2image(args)

    if args.flip:
        # flip it
        img = np.flipud(img)

    # convert to image
    pic = Image.fromarray(img)

    if args.showimage:
        # show image
        pic.show()

    # write image file (png)
    pic.save(args.image.name)

    return 0

if __name__ == '__main__':
    sys.exit(main())
