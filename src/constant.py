#!/usr/bin/env python
# coding=utf-8
__version__ = "0.2.0"
"""
Constants declaration for the catgen.py script.

"""

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
