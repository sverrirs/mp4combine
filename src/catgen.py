#!/usr/bin/env python
# coding=utf-8
__version__ = "0.2.0"
"""
Python script that generates the necessary mp4box -cat commands to concatinate multiple video files 
together and generates a chapter file that marks the beginning of each concatenated file in the final result.

This script requires the GPAC package to be installed with the mp4box command line utility.
https://gpac.wp.mines-telecom.fr/downloads/

The script is written in Python 3.5

Requires:
  pip install humanize

See: https://github.com/sverrirs/mp4box-catgen
Author: Sverrir Sigmundarson  info@sverrirs.com  https://www.sverrirs.com
"""
from constant import DISKSIZES, ABSSIZES # Constants for the script

import humanize # Display human readible values for sizes etc
import sys, os, re
from pathlib import Path # to check for file existence in the file system
import argparse # Command-line argument parser
import ntpath # Used to extract file name from path for all platforms http://stackoverflow.com/a/8384788
import glob # Used to do partial file path matching when listing file directories in search of files to concatinate http://stackoverflow.com/a/2225582/779521
import subprocess # To execute shell commands 
import re # To perform substring matching on the output of mp4box and other subprocesses
from datetime import timedelta # To store the parsed duration of files and calculate the accumulated duration

#
# Provides natural string sorting (numbers inside strings are sorted in the correct order)
# http://stackoverflow.com/a/3033342/779521
def natural_key(string_):
  """See http://www.codinghorror.com/blog/archives/001018.html"""
  return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]

#
# The main entry point for the script
def runMain():
  # Compile the regular expressions
  regex_mp4box_duration = re.compile(r"Computed Duration (?P<hrs>[0-9]{2}):(?P<min>[0-9]{2}):(?P<sec>[0-9]{2}).(?P<msec>[0-9]{3})", re.MULTILINE)

  # Construct the argument parser for the commandline
  args = parseArguments()

  # Get the mp4box exec
  mp4exec = findMp4Box(args.gpac)

  # Detect the maximum file size that should be generated, if <=0 then unlimited
  max_out_size = determineMaximumOutputfileSize(args.size, args.disk)
  print( "Max Out Size: {0}".format(humanize.naturalsize(max_out_size, gnu=True)) )

  # Create the output file names both for the video file and the intermediate chapters file
  path_out_file = Path(args.output)
  path_chapters_file = path_out_file.with_suffix('.txt') # Just change the file-extension of the output file to TXT

  # If the output files exist then either error or overwrite
  if( path_out_file.exists() ):
    if( args.overwrite ):
      os.remove(str(path_out_file))
    else:
      print( "Output file '{0}' already exists. Use --overwrite switch to overwrite.".format(path_out_file.name))
      sys.exit(0)

  # Get all the input files
  in_files = getFileNamesFromGrepMatch(args.match, path_out_file)
  if( in_files is None ):
    print( "No mp4 video files found matching '{0}'".format(args.match))
    sys.exit(0)

  file_infos = []
  # Only process files that have file-ending .mp4 and not files that have the same name as the joined one
  for in_file in in_files:
    print("File: {0}".format(in_file))
    file_infos.append(parseMp4boxMediaInfo(in_file, mp4exec, regex_mp4box_duration))

  # If nothing was found then don't continue, this can happen if no mp4 files are found or if only the joined file is found
  if( len(file_infos) <= 0 ):
    print( "No mp4 video files found matching '{0}'".format(args.match))
    sys.exit(0)

  print("Found {0} files".format(len(file_infos)))

  # Now segment the files found and their infos into chunks that fit the size limits

  
  # Now generate the cat operation for each segment
  seg_files = []
  chapters = []
  cumulative_dur = timedelta(seconds=0)
  cumulative_size = 0
  seg_files_created = 0
  for file_info in file_infos:
    # When the cumulative_size will become greater than the maximum size then call the creation function and reset the counters for the segment
    if( max_out_size > 0 and cumulative_size + file_info['size'] > max_out_size ):
      # Creat the output file
      seg_files_created += 1
      createCombinedVideoFile(seg_files, chapters, cumulative_dur, cumulative_size, mp4exec, path_out_file, path_chapters_file, args.overwrite, seg_files_created )
      # Reset the loop variables
      seg_files = []
      chapters = []
      cumulative_dur = timedelta(seconds=0)
      cumulative_size = 0

    # Collect the file info data and continue to the next file
    seg_files.append(file_info['file'])
    chapters.append({"name": Path(file_info['file']).stem, "timecode":formatTimedelta(cumulative_dur)})
    cumulative_dur += file_info['dur'] # Count the cumulative duration
    cumulative_size += file_info['size']    

  # After the loop, create the final output file
  if( seg_files_created > 0 ):
    seg_files_created += 1 # Increment the seg files only if it has already been incremented
  createCombinedVideoFile(seg_files, chapters, cumulative_dur, cumulative_size, mp4exec, path_out_file, path_chapters_file, args.overwrite, seg_files_created )
  
  print("Videos combined sucessfully!")

#
# Creates a combined video file for a segment
def createCombinedVideoFile(seg_files, chapters, cumulative_dur, cumulative_size, mp4exec, path_out_file, path_chapters_file, args_overwrite, seg_files_created ):

  # If we're creating segmentation files then this variable will contain the current number of the segment
  # if we're only creating a single file then this value will be zero and only one output file will be generated ever
  path_out_seg_file = path_out_file
  if( seg_files_created > 0 ):
    # Join the seg number with the file name
    dirpath = os.path.dirname(str(path_out_file))
    path_out_seg_file = Path(os.path.join(dirpath, "{0}_{1}{2}".format(path_out_file.stem, str(seg_files_created).zfill(3), path_out_file.suffix)))

  # If the output files exist then either error or overwrite
  if( path_out_seg_file.exists() ):
    if( args_overwrite ):
      os.remove(str(path_out_seg_file))
    else:
      print( "Output file '{0}' already exists. Use --overwrite switch to overwrite.".format(path_out_seg_file.name))
      sys.exit(0)

  print( "Output: {0}".format(str(path_out_seg_file)))
  
  # Add the final chapter as the end for this segment
  chapters.append({"name": "End", "timecode":formatTimedelta(cumulative_dur)})

  # Chapters should be +1 more than files as we have an extra chapter ending at the very end of the file
  print("{0} chapters, {1} running time, {2} total size".format( len(chapters), formatTimedelta(cumulative_dur), humanize.naturalsize(cumulative_size, gnu=True)))

  # Write the chapters file to out
  saveChaptersFile(chapters, path_chapters_file)

  # Now create the combined file and include the chapter marks
  saveCombinedVideoFile(mp4exec, seg_files, path_out_seg_file, path_chapters_file)

  # Delete the chapters file
  os.remove(str(path_chapters_file))

#
# Attempts to detect the requested size of the output file based on the input parameters
# the absolute_size is overridden by disk_capacity if both are specified
def determineMaximumOutputfileSize(absolute_size, disk_capacity):
  if( disk_capacity and disk_capacity in DISKSIZES ):
    dsk_cap = DISKSIZES[disk_capacity]
    #print( "Disk Capacity: {0}".format(dsk_cap))
    return dsk_cap
  elif( absolute_size):
    #print( "Absolute size: "+absolute_size)
    # First remove all spaces from the size string and convert to uppercase, remove all commas from the string
    # now attempt to parse the sizes
    abs_size = "".join("".join(absolute_size.split(' ')).split(',')).upper()
    regex_size_parse = re.compile(r"^(?P<size>[0-9]*(?:\.[0-9]*)?)\s*(?P<unit>GB|MB|KB|B|TB)?$", re.MULTILINE)

    match = regex_size_parse.search( absolute_size )
    size = float(match.group("size"))
    unit = match.group("unit")
    #print( "Absolute value: {0}, unit: {1} ".format(size, unit))
    if( not unit or not unit in ABSSIZES ):
      unit = "MB"  # Default is megabytes if nothing is specified
    unit_multiplier = ABSSIZES[unit]
    total_size = size * unit_multiplier
    #print( "Absolute total: {0}, mult: {1} ".format(total_size, unit_multiplier))
    return total_size
  else:
    # If nothing is specified then the default return is to use unbounded
    return -1
  
#
# Executes the mp4box app with the -info switch and 
# extracts the track length and file size from the output
def parseMp4boxMediaInfo(file_name, mp4box_path, regex_mp4box_duration):
  
  # Get the size of the file in bytes
  statinfo = os.stat(file_name)
  file_size = statinfo.st_size #Size in bytes of a plain file

  # Run the app and collect the output
  ret = subprocess.run([mp4box_path, "-info", "-std", file_name], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

  # Ensure that the return code was ok before continuing
  ret.check_returncode()

  # Computed Duration 00:23:06.040 - Indicated Duration 00:23:06.040
  match = regex_mp4box_duration.search( ret.stdout )
  hrs = int(match.group("hrs"))
  min = int(match.group("min"))
  sec = int(match.group("sec"))
  msec = int(match.group("msec"))

  duration = timedelta(days=0, hours=hrs, minutes=min, seconds=sec, milliseconds=msec )
  return {'file':file_name, 'size':file_size, 'dur':duration }

#
# Locates the mp4box executable and returns a full path to it
def findMp4Box(path_to_gpac_install=None):
  
  if( not path_to_gpac_install is None and os.path.isfile(os.path.join(path_to_gpac_install, "mp4box.exe")) ):
    return os.path.join(path_to_gpac_install, "mp4box.exe")
  
  # Attempts to search for it under C:\Program Files\GPAC
  if( os.path.isfile("C:\\Program Files\\GPAC\\mp4box.exe")):
    return "C:\\Program Files\\GPAC\\mp4box.exe"
  
  # For 32 bit installs
  if( os.path.isfile("C:\\Program Files\\GPAC\\mp4box.exe")):
    return "C:\\Program Files (x86)\\GPAC\\mp4box.exe"
  
  # Throw an error
  raise ValueError('Could not locate GPAC install, please use the --gpac switch and ensure that the mp4box.exe file was installed.')

#
# Returns an array of files matching the grep string passed in
def getFileNamesFromGrepMatch(grep_match, path_out_file):
   in_files = glob.glob(grep_match.replace("\\", "/"))
   return [f for f in sorted(in_files, key=natural_key) if '.mp4' in Path(f).suffix and not Path(f) == path_out_file]

#
# Cleans any invalid file name and file path characters from the given filename
def sanitizeFileName(local_filename, sep=" "):
  #These are symbols that are not "kosher" on a NTFS filesystem.
  local_filename = re.sub(r"[\"/:<>|?*\n\r\t\x00]", sep, local_filename)
  return local_filename

#
# Creates a nice format of a datetime.timedelta structure, including milliseconds
def formatTimedelta(time_delta):
  timecode_s = time_delta.seconds
  timecode_ms = int(time_delta.microseconds / 1000)
  return '{:02}:{:02}:{:02}.{:03}'.format(timecode_s // 3600, timecode_s % 3600 // 60, timecode_s % 60, timecode_ms)

#
# Saves a list of chapter information to a chapter file in the common chapter syntax
def saveChaptersFile( chapters, path_chapters_file):
  # Make sure that the directory exists and then write the full list of pids to it
  if not path_chapters_file.parent.exists():
    path_chapters_file.parent.mkdir(parents=True, exist_ok=True)

  # If the chapters file is already there, delete it
  if os.path.exists(str(path_chapters_file)):
    os.remove(str(path_chapters_file))
  
  # Writing the common CHAPTER syntax
  # Common syntax : CHAPTERX=h:m:s[:ms or .ms] on one line and CHAPTERXNAME=name on the other – the order is not important but chapter lines MUST be declared sequencially (same X value expected for 2 consecutive lines).
  chapter_idx = 1
  with path_chapters_file.open(mode='w+', encoding='utf-8') as theFile:
    for chapter in chapters:
      theFile.write("CHAPTER{0}={1}\n".format(chapter_idx, chapter['timecode']))
      theFile.write("CHAPTER{0}NAME=\"{1}\"\n".format(chapter_idx, chapter['name']))
      chapter_idx += 1

#
# Calls mp4box to create the concatinated video file and includes the chapter file as well
def saveCombinedVideoFile(mp4box_path, video_files, path_out_file, path_chapters_file):

  # First delete the existing out video file
  if os.path.exists(str(path_out_file)):
    os.remove(str(path_out_file))

  # Construct the args to mp4box
  prog_args = [mp4box_path]
  for video_file in video_files:
    prog_args.append("-cat")
    prog_args.append(str(Path(video_file)))
  
  # Add the chapter file
  prog_args.append("-chap")
  prog_args.append(str(path_chapters_file))

  # Add the output file at the very end
  prog_args.append(str(path_out_file))

  # Run the app and collect the output
  #ret = subprocess.run(prog_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
  ret = subprocess.Popen(prog_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)

  longest_line = 0
  while True:
    try:
      line = ret.stdout.readline()
      if not line:
        break
      line = line.strip()[:65] # Limit the max length of the line, otherwise it will screw up our console window
      longest_line = max( longest_line, len(line))
      sys.stdout.write('\r '+line.ljust(longest_line))
      sys.stdout.flush()
    except UnicodeDecodeError:
      continue # Ignore all unicode errors, don't care!

  # Ensure that the return code was ok before continuing
  retcode = ret.poll()
  while retcode is None:
    retcode = ret.poll()

  # Move the input to the beginning of the line again
  # subsequent output text will look nicer :)
  sys.stdout.write('\r')

  if( retcode != 0 ):
    print()
    print( "Error while concatinating file")
  return retcode


def parseArguments():
  parser = argparse.ArgumentParser()
  
  parser.add_argument("-o", "--output", help="The path and filename of the concatenated output file. If multiple files then the script will append a number to the filename.",
                                        type=str)

  parser.add_argument("-m","--match",   help="A grep style match that should be used to detect files to concatinate.",
                                        type=str)                                        

#  parser.add_argument("-f","--files",   help="The list of files that should be concatinated",
#                                        type=str, nargs="+")
  
  parser.add_argument('--disk',          help="When defined this defines the maximum file size to generate so that they will fit the required optical disk capacity. dvd4=4.7GB, dvd8=8.5GB, br25=25GB. If specified this overrides the -s/--size argument.",
                                        choices=['dvd4', 'dvd8', 'br25'])

  parser.add_argument("-s", "--size",   help="Defines the maximum size of a single combined output file. Supports format ending such as 'MB' for megabytes, 'GB' for gigabytes. If nothing is specified then 'MB' is assumed. Overridden by the --disk argument if both are specified. Supports only numbers using dot (.) as decimal separator, e.g. '15.5GB'", type=str)

  parser.add_argument("--gpac",         help="Path to the GPAC install directory", 
                                        type=str)

  parser.add_argument("--overwrite",     help="Existing files with the same name as the output will be silently overwritten.", 
                                        action="store_true")
  
  parser.add_argument("-d", "--debug",  help="Prints out extra debugging information while script is running", 
                                        action="store_true")


  return parser.parse_args()


# If the script file is called by itself then execute the main function
if __name__ == '__main__':
  runMain()