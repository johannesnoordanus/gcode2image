#!/usr/bin/env python3
"""
gcode2image: convert gcode to image.
"""
__version__ = "2.4.0"

import sys
import re
import argparse
from PIL import Image
import numpy as np

# set to 10 pixels per mm
DEFAULT_RESOLUTION = .1

# max_laser_power
DEFAULT_MAX_LASER_POWER = 255

def gcode2image(args) -> np.array:
    """
    Convert gcode to array using header info from .gc(ode) file.
    """
    # gcode: TextIO

    # set args
    gcode = args.gcode

    float_pattern = "[+\-]?[0-9]+(\.[0-9]+)?"

    X_pattern = f"X{float_pattern}"
    Y_pattern = f"Y{float_pattern}"
    S_pattern = "S[0-9]+"

    gcode_pattern = "^(G0|G00|G1|X|Y|M4|M3|M5|M2|S)"

    invert_intensity = True

    def line_slope(p1: (int,int), p2: (int,int)):
        """Calculate the slope of the line p1p2"""
        x1, y1 = p1[0], p1[1]
        x2, y2 = p2[0], p2[1]

        if x1 == x2:
            return 1

        return (y1 - y2) / (x1 - x2)

    def line_offset(p1: (int,int), p2: (int,int)):
        """Calculate the offset of the line p1p2 from the origin"""
        x1, y1 = p1[0], p1[1]

        return y1 - line_slope(p1, p2) * x1

    def line(x, slope, offset):
        y = slope * x + offset
        return round(y)

    def draw(img, start: (int,int), end: (int,int), color):
        slope = line_slope(start, end)
        offset = line_offset(start, end)

        #print(f"DRAW: start {start}, end {end}, color {color}")
        if slope == 1 and ((start[0] - end[0]) != (start[1] - end[1])):
            # vertical line (not a 45 degrees line)
            diy = 1 if end[1] > start[1] else -1
            for y2 in range(start[1], end[1] + diy, diy):
                if img[y2,start[0]] != 255:
                    img[y2,start[0]] = max(img[y2,start[0]] - color, 0)
                else:
                    img[y2,start[0]] = color
        else:
            # non vertical line
            dix = 1 if end[0] > start[0] else -1
            prev = start
            for x in range(start[0], end[0] + dix, dix):
                y = line(x,slope,offset)
                if abs(y - prev[1]) > 1:
                    di = 1 if y > prev[1] else -1
                    for y1 in range(prev[1], y, di):
                        #print("y1:",(x,y1))
                        if img[y1,x] != 255:
                            img[y1,x] = max(img[y1,x] - color, 0)
                        else:
                            img[y1,x] = color

                if x != end[0]:
                    if img[y,x] != 255:
                        img[y,x] = max(img[y,x] - color, 0)
                    else:
                        img[y,x] = color
                #print("draw:",(x,y))

                prev = (x,y)

    def pixel_range(ra, dY, dX, pixelsize, img_height, img_width):
        """
        Make range fit within window
        """
        dYmin = round(dY/pixelsize) if round(dY/pixelsize)-int(ra) < 0 else round(dY/pixelsize)-int(ra)
        dYplus = round(dY/pixelsize) if round(dY/pixelsize)+int(ra) > img_height else round(dY/pixelsize)+int(ra)
        dXmin = round(dX/pixelsize) if round(dX/pixelsize)-int(ra) < 0 else round(dX/pixelsize)-int(ra)
        dXplus = round(dX/pixelsize) if round(dX/pixelsize)+int(ra) > img_width else round(dX/pixelsize)+int(ra)

        return (dYmin, dYplus, dXmin, dXplus)

    def pixel_intensity(S: int = None) -> int:
        # max_laser_power
        # pixel intensity (inverse) proportional to laser power
        return round((1.0 - float(S/max_laser_power)) * 255) if invert_intensity else round(float(S/max_laser_power) * 255)

    def draw_line(X: int, Y: int, S: int = None):
        nonlocal x
        nonlocal y
        nonlocal X_start
        nonlocal Y_start
        nonlocal S_current

        if X != x or Y != y:
            if (G1_mode and (M3_mode or M4_mode)) or (G0_mode and G0_gray):
                # draw line
                draw(image, (x - X_start,y - Y_start),(X - X_start,Y - Y_start), pixel_intensity(S if S is not None else G0_gray))
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
                elif 'Z' in line:
                    print(f"Error: Z-coordinates are unsupported (images are 2-D), line: {line}, exit ...")
                    sys.exit(1)
                elif 'M2' in line:
                    # program end: stop
                    break

    def get_gcode_info():
        nonlocal gcode
        gc_info = { 'min_X': None, 'min_Y': None, 'max_X': None, 'max_Y': None, 'max_S': None, 'pixelsize': None, 'M': None, 'max_laser_power': None }

        while True:
            line = gcode.readline()

            if line == '':
                # exit at EOF
                break
            if re.search(gcode_pattern, line):
                X = re.search(X_pattern,line)
                if X:
                    X = float(X.group(0)[1:])
                    gc_info['min_X'] = X if not gc_info['min_X'] or X < gc_info['min_X'] else gc_info['min_X']
                    gc_info['max_X'] = X if not gc_info['max_X'] or X > gc_info['max_X'] else gc_info['max_X']
                Y = re.search(Y_pattern,line)
                if Y:
                    Y = float(Y.group(0)[1:])
                    gc_info['min_Y'] = Y if not gc_info['min_Y'] or Y < gc_info['min_Y'] else gc_info['min_Y']
                    gc_info['max_Y'] = Y if not gc_info['max_Y'] or Y > gc_info['max_Y'] else gc_info['max_Y']

                S = re.search("S[0-9]+",line)
                if S:
                    S = float(S.group(0)[1:])
                    gc_info['max_S'] = S if not gc_info['max_S'] or S > gc_info['max_S'] else gc_info['max_S']

                M = re.search("M[34]+",line)
                if M:
                    gc_info['M'] = True

            if line.find("pixelsize") >= 0:
                # find a line that starts with ';' followed by 'pixelsize' (possibly a ':'), one or more spaces and a float
                pixelsize = re.search(f"^;.*pixelsize:? +{float_pattern}", line)
                if pixelsize:
                    pixelsize = re.search(f"pixelsize:? +{float_pattern}", pixelsize.group()).group()
                    gc_info['pixelsize'] = float(re.search(f"{float_pattern}", pixelsize).group())

            if line.find("maximum_image_laser_power") >= 0:
                # find a line that starts with ';' followed by 'pixelsize' (possibly a ':'), one or more spaces and a float
                max_laser_power = re.search(f"^;.*maximum_image_laser_power:? +{float_pattern}", line)
                if max_laser_power:
                    max_laser_power = re.search(f"maximum_image_laser_power:? +{float_pattern}", max_laser_power.group()).group()
                    gc_info['max_laser_power'] = float(re.search(f"{float_pattern}", max_laser_power).group())

        return gc_info

    #
    # gcode2image
    #

    # first pass: find min max of coordinates and S value, find pixelsize
    gc_info = get_gcode_info()

    if gc_info['min_X'] is None or gc_info['min_Y'] is None or gc_info['max_X'] is None or gc_info['max_Y'] is None:
        print(f"Error: gcode file not well formed: missing move commands (X<nr> and or Y<nr> coordinates), exit ...")
        sys.exit(1)

    # handle resolution
    if args.resolution is not None:
        if gc_info['pixelsize'] and gc_info['pixelsize'] != args.resolution:
            print(f"Note: conflicting settings: option '--resolution' {args.resolution} differs from {gc_info['pixelsize']} found in '{args.gcode.name}'")
            print(f"pixelsize set to {args.resolution}")
        pixelsize = args.resolution
    elif gc_info['pixelsize']:
        print(f"option '--resolution' is not supplied, pixel size set to {gc_info['pixelsize']} (found within '{args.gcode.name}')")
        pixelsize = gc_info['pixelsize']
    else:
        print(f"pixelsize set to default {DEFAULT_RESOLUTION} (pixelsize is not set by option '--resolution' or found in '{args.gcode.name}')")
        pixelsize = DEFAULT_RESOLUTION

    # handle pixel intensity
    if args.maxintensity is not None:
        max_laser_power = args.maxintensity
    elif gc_info['max_laser_power']:
        max_laser_power = gc_info['max_laser_power']
        print(f"maxintensity is set to {max_laser_power} (found within '{args.gcode.name}')")
    else:
        max_S = gc_info['max_S']
        if max_S and max_S > DEFAULT_MAX_LASER_POWER:
            # self calibrate
            max_laser_power = max_S
        else:
            max_laser_power = DEFAULT_MAX_LASER_POWER
        print(f"maxintensity is set to {max_laser_power} (option '--maxintensity' is not supplied or found in '{args.gcode.name}')")

    # handle missing G1 and M3(4) commands
    M = gc_info['M']
    max_S = gc_info['max_S']
    if not (M and max_S):
        print("Warning: gcode does not contain write movements and or writing mode 'M3(4)' commands: no image produced (use option --showG0 to see movements only)")

    # set gray intensity
    G0_gray = max_laser_power/5 if args.showG0 else 0

    # save image lower left
    img_min_X = gc_info['min_X']
    img_min_Y = gc_info['min_Y']

    if args.showorigin:
        # set possibly new lower left upper right for image to include the origin
        gc_info['min_X'] = 0 if 0 < gc_info['min_X'] else gc_info['min_X']
        gc_info['max_X'] = 0 if 0 > gc_info['max_X'] else gc_info['max_X']
        gc_info['min_Y'] = 0 if 0 < gc_info['min_Y'] else gc_info['min_Y']
        gc_info['max_Y'] = 0 if 0 > gc_info['max_Y'] else gc_info['max_Y']

        # X/Y start is used by 'draw_line' as offset
        X_start = round(gc_info['min_X']/pixelsize)
        Y_start = round(gc_info['min_Y']/pixelsize)

        # set current (x,y) and correct for possibly new origin
        x = round((gc_info['min_X'] + abs(gc_info['min_X'] - img_min_X))/pixelsize)
        y = round((gc_info['min_Y'] + abs(gc_info['min_Y'] - img_min_Y))/pixelsize)
    else:
        # X/Y start is used by 'draw_line' as offset
        X_start = round(gc_info['min_X']/pixelsize)
        Y_start = round(gc_info['min_Y']/pixelsize)

        # set current (x,y)
        x = X_start
        y = Y_start

    # set image dimensions
    img_height = abs(round(gc_info['max_Y']/pixelsize) - round(gc_info['min_Y']/pixelsize))
    img_width = abs(round(gc_info['max_X']/pixelsize) - round(gc_info['min_X']/pixelsize))

    # init image
    image = np.full([img_height + 1, img_width + 1], 255, dtype=np.uint8)
    print(f"image pixels: {image.shape[1] - 1} x {image.shape[0] - 1} (WidthxHeight)")

    # init modes (gcode)
    M4_mode = False
    M3_mode = False
    G0_mode = False
    G1_mode = False

    # init S value
    S_current = None

    # second pass: draw image lines
    gcode.seek(0)
    parse_lines()
    # calculate origin
    dX = -img_min_X if min(0.0, img_min_X) != 0.0 else 0.0
    dY = -img_min_Y if min(0.0, img_min_Y) != 0.0 else 0.0

    # show grid if requested
    if args.grid:
        # make grid 10mm x 10mm

        # draw grid X lines
        for i in range(round((dX%10)/pixelsize), image.shape[1], round(10/pixelsize)):
            image[:,i:i+1] = 180
        # draw grid Y lines
        for i in range(round((dY%10)/pixelsize), image.shape[0], round(10/pixelsize)):
            image[i:i+1,:] = 180

    # show origin if requested
    if args.showorigin:
        # calibrate line width
        line_width_factor = max(round(.00053 * image.shape[1]),1)

        # get the right pixel ranges to keep within array borders
        ra8 = pixel_range(4 * line_width_factor, dY, dX, pixelsize, img_height, img_width)

        # show origin
        image[ra8[0]:ra8[1], ra8[2]:ra8[3]] = 100

        # get pixel range of X/Y-axis lines
        ra2 = pixel_range(1.5 * line_width_factor, dY, dX, pixelsize, img_height, img_width)

        # draw X/Y axis lines
        image[ra2[0]:ra2[1],0:img_width] = 100
        image[0:img_height,ra2[2]:ra2[3]] = 100

        # draw X-axis line markers
        for i in range(0,round(img_width/pixelsize), 10):
            #image[dYmin8:dYplus8,i] = 0
            ra = pixel_range(2 * line_width_factor, dY, i + (dX%10), pixelsize, img_height, img_width)
            iXmin = ra[2]
            iXplus = ra[3]
            image[ra8[0]:ra8[1],iXmin:iXplus] = 100

        # draw Y-axis line markers
        for i in range(0,round(img_height/pixelsize), 10):
            ra = pixel_range(2 * line_width_factor, i + (dY%10), dX, pixelsize, img_height, img_width)
            iYmin = ra[0]
            iYplus = ra[1]
            image[iYmin:iYplus,ra8[2]:ra8[3]] = 100

    return image

def main() -> int:
    """
    main
    """

    pixelsize_default = None
    max_laser_power_default = None

    # Define command line argument interface
    parser = argparse.ArgumentParser(description='Convert a gcode file to image.')
    parser.add_argument('gcode', type=argparse.FileType('r'), default = sys.stdin, help='name of gcode file to convert')
    parser.add_argument('image', type=argparse.FileType('w'), help='image out')
    parser.add_argument('--resolution', default=pixelsize_default, metavar=f"<default: {DEFAULT_RESOLUTION}>",
        type=float, help="define image resolution by pixel size (mm^2)")
    parser.add_argument('--maxintensity', default=max_laser_power_default, metavar=f"<default: {DEFAULT_MAX_LASER_POWER}>",
        type=float, help="set maximum intensity for this image, typically 'max laser power' of the source gcode file")
    parser.add_argument('--showimage', action='store_true', default=False, help='show b&w converted image' )
    parser.add_argument('--showG0', action='store_true', default=False, help='show G0 moves' )
    parser.add_argument('--showorigin', action='store_true', default=False, help='show image origin (0,0)' )
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
