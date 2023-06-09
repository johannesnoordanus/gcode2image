# gcode2image

Convert gcode to pixel exact image files.
Images can be shown with axes and grid to check laser cutter (CNC) start coordinates and image parameters.

gcode2image can be used alongside *grblhud*, *image2gcode* and *svg2gcode* for a commandline driven workflow. (https://github.com/johannesnoordanus/.)

### Install:
Depends on python libraries numpy, PIL, skimage and mathplot *pip install ..*. </br>
```
> 
> pip install gcode2image
```
### Usage:
```
> gcode2image --help
usage: gcode2image [-h] [--showimage] [--showaxes] [--showG0] [--offset] [--flip] [-V] gcode image

Convert a gcode file to image.

positional arguments:
  gcode          name of gcode file to convert
  image          image out

options:
  -h, --help     show this help message and exit
  --showimage    show b&w converted image
  --showaxes     show image with xy-axis
  --showG0       show G0 moves
  --offset       show image offset
  --flip         flip image updown
  --grid         show a grid 10mm wide
  -V, --version  show version number and exit
```
