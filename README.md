# gcode2image

Commanline tool to convert gcode to pixel exact image files.

This 2D viewer - images are 2D (no Z coordinates) - has as strong points that it shows gray levels and thus is able to show a realistic representation of laser engravings. Images can be viewed while converting gcode and the exact placing and size of the gcode can be shown. Since version 2.4.0 repeated writes to the same pixel locations are shown. This means that the simulated engraving is pretty close to actual laser engraving.
It is also possible to show speed movement *G0* code.

A typical command:
```gcode2image --showimage --flip test.gc test.png```

This converts gcode file ```test.gc``` to image file ```test.png```. (You can change the image file extension to *.jpg* or other, to get another image file format.) It shows the result image in an external viewer (platform dependent) and flips the image upside down because the gcode coordinate system and image coordinate system differ.

To get a precise idea of the location and orientation of the gcode, the following options can be used:

```gcode2image --showimage --flip --showorigin --grid test.gc test.png```

This generates a 1 cm (per axis) grid and shows the origin X0Y0.

*gcode2image* can be used alongside *grblhud*, *image2gcode* and *svg2gcode* for a commandline driven workflow. (https://github.com/johannesnoordanus/.)

Please consider supporting me, so I can make this application better and add new functionality to it: <http://paypal.me/johannesnoordanus/5,00>

### Install:
Depends on python libraries numpy, PIL and skimage.
*pip install* takes care of that.
```
> pip install gcode2image
```
### Usage:
```
$ gcode2image --help
usage: gcode2image [-h] [--resolution <default: 0.1>] [--maxintensity <default: 255>] [--showimage] [--showG0] [--showorigin] [--flip] [--grid] [-V] gcode image

Convert a gcode file to image.

positional arguments:
  gcode                 name of gcode file to convert
  image                 image out

options:
  -h, --help            show this help message and exit
  --resolution <default: 0.1>
                        define image resolution by pixel size (mm^2)
  --maxintensity <default: 255>
                        set maximum intensity for this image, typically 'max laser power' of the source gcode file
  --showimage           show b&w converted image
  --showG0              show G0 moves
  --showorigin          show image origin (0,0)
  --flip                flip image updown
  --grid                show a grid 10mm wide
  -V, --version         show version number and exit
```
### Example:
A rectangle in gcode:
```
M4 S300         ; set write mode (constant burn) and intensity
G0 X0Y0         ; move head to X0 Z0
G1 X25          ; move head to X25 and burn with intensity 300 (moves head on the X-axis)
G1 Y25          ; move head to Y25 and burn with intensity 300  (moves head on the Y-axis)
G1 X0           ; move head to X0 and burn with intensity 300  (moves head back on X-axis)
G1 Y0           ; moves head to Y0 and burn with intensity 300 (moves head beck on the Y-axis)
```

Make a file 'testje.gc' (for example) and add the above lines.
Run it:
```gcode2image --showimage --flip testje.gc testje.png```

This results in image file ```testje.png``` that has the square at the borders (note that gcode2image outputs the minimum number of pixels in X and Y)

If you add the below line at the end of the gcode file, an extra line from (0,0) to the centre of the image will show up.
This will make it easier to see the result.

```G1 X12.5Y12.5   ; move head to centre and burn with intensity```

```gcode2image --showimage --flip --showorigin --grid --showG0 testje.gc testje.png```

This will show the origin (X0Y0), a grid and the gcode image containing a line from the origin to the centre of the screen.
