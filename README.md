# gcode2image

Convert gcode to pixel exact image files.
Images can be shown with axes to check laser cutter (CNC) start coordinates and image parameters.

gcode2image can be used alongside grblhud.py, image2gcode.py and svg2gcode.py for a commandline driven workflow. (https://github.com/johannesnoordanus/grblhud, https://github.com/johannesnoordanus/image2gcode and https://github.com/johannesnoordanus/svg2gcode resp.)

### Install:
Depends on python libraries numpy, PIL, skimage and mathplot (pip install ..). </br>
Download 'gcode2image.py' and 'install' to a directory within ```$PATH``` (or within python path).</br>
Then:
```
> cd <above dir>
> chmod u+x gcode2image.py    # to make it executable; thats it!
```
### Usage:
```
> python3 gcode2image.py --help
usage: gcode2image.py [-h] [--showimage] [--showaxes] [--showG0] [--offset] [--flip] [-V] gcode image

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
