#!/usr/bin/env python
# coding=utf-8
__version__ = "2.1.0"
"""
Constants declaration for the combine.py script.

See: https://github.com/sverrirs/mp4combine
Author: Sverrir Sigmundarson  info@sverrirs.com  https://www.sverrirs.com
"""
import sys
from termcolor import colored # For shorthand color printing to the console, https://pypi.python.org/pypi/termcolor

# Most DVD±R/RWs are advertised using the definition of 1 Gigabyte = 1,000,000,000 bytes
# instead of the more traditional definition of 1 GB = 1,073,741,824 bytes = 1 Gibibyte.
DVD_4GB = 4700000000 #DVD+R 4.7GB
DVD_8GB = 8500000000 #DVD+R 8.5GB
BR_25GB = 25000000000 #BluRay-R 25GB

DISKSIZES = {}
DISKSIZES['dvd4'] = DVD_4GB
DISKSIZES['dvd8'] = DVD_8GB
DISKSIZES['br25'] = BR_25GB

ABSSIZES={}
ABSSIZES['B'] = 1
ABSSIZES['KB'] = ABSSIZES['B'] * 1024
ABSSIZES['MB'] = ABSSIZES['KB'] * 1024
ABSSIZES['GB'] = ABSSIZES['MB'] * 1024
ABSSIZES['TB'] = ABSSIZES['GB'] * 1024

class Colors(object):
  # Lambdas as shorthands for printing various types of data
  # See https://pypi.python.org/pypi/termcolor for more info
  filename = lambda x: colored(x, 'cyan')
  #color_pid_title = lambda x: colored(x, 'red', 'on_cyan')
  toolpath = lambda x: colored(x, 'yellow')
  #color_sid = lambda x: colored(x, 'yellow')
  #color_description = lambda x: colored(x, 'white')
  fileout = lambda x: colored(x, 'green')
  success = lambda x: colored(x, 'green')
  #color_progress_remaining = lambda x: colored(x, 'white')
  #color_progress_percent = lambda x: colored(x, 'green')