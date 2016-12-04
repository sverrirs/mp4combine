#!/usr/bin/env python
# coding=utf-8
__version__ = "0.1.0"
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

import humanize # Display human readible values for sizes etc
import sys, os, re
from pathlib import Path # to check for file existence in the file system
import argparse # Command-line argument parser
import ntpath # Used to extract file name from path for all platforms http://stackoverflow.com/a/8384788
import glob # Used to do partial file path matching when listing file directories in search of files to concatinate http://stackoverflow.com/a/2225582/779521
import subprocess # To execute shell commands 
import re # To perform substring matching on the output of mp4box and other subprocesses
from datetime import timedelta # To store the parsed duration of files and calculate the accumulated duration

# The main entry point for the script
def runMain():
  # Compile the regular expressions
  regex_mp4box_duration = re.compile(r"Computed Duration (?P<hrs>[0-9]{2}):(?P<min>[0-9]{2}):(?P<sec>[0-9]{2}).(?P<msec>[0-9]{3})", re.MULTILINE)

  # Construct the argument parser for the commandline
  args = parseArguments()

  # Get the mp4box exec
  mp4exec = findMp4Box(args.gpac)

  # Now execute the thing for all the params
  in_files = getFileNamesFromGrepMatch(args.match)

  if( in_files is None ):
    print( "No files found matching '{0}'".format(args_match))
    sys.exit(0)

  file_infos = []

  for in_file in in_files:
    print("File: {0}".format(in_file))
    file_infos.append(parseMp4boxMediaInfo(in_file, mp4exec, regex_mp4box_duration))

  print("Found {0} files".format(len(file_infos)))
  
  # Now generate the cat operation
  chapters = []
  cumulative_dur = timedelta(seconds=0)
  cumulative_size = 0
  for file_info in file_infos:
    chapters.append({"name": Path(file_info['file']).stem, "timecode":formatTimedelta(cumulative_dur)})
    cumulative_dur += file_info['dur'] # Count the cumulative duration
    cumulative_size += file_info['size']
  
  # Add the final chapter as the end
  chapters.append({"name": "End", "timecode":formatTimedelta(cumulative_dur)})

  # Chapters should be +1 more than files as we have an extra chapter ending at the very end of the file
  print("{0} chapters, {1} running time, {2} total size".format( len(chapters), formatTimedelta(cumulative_dur), humanize.naturalsize(cumulative_size, gnu=True)))

  # Check the output file path variables and construct all files needed
  path_out_file = Path(args.output)
  path_chapters_file = path_out_file.with_suffix('.txt') # Just change the file-extension of the output file to TXT

  # Write the chapters file
  saveChaptersFile(chapters, path_chapters_file)

  # Now create the combined file and include the chapter marks
  saveCombinedVideoFile(mp4exec, in_files, path_out_file, path_chapters_file)
  
  print("Videos combined sucessfully!")
  
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
def getFileNamesFromGrepMatch(grep_match):
  return glob.glob(grep_match.replace("\\", "/"))

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
    print( "Error while concatinating file")
  return retcode


def parseArguments():
  parser = argparse.ArgumentParser()
  
  parser.add_argument("-o", "--output", help="The path and filename of the concatenated output file. If multiple files then the script will append a number to the filename.",
                                        type=str)

  parser.add_argument("-m","--match",   help="A grep style match that should be used to detect files to concatinate.",
                                        type=str)                                        

  parser.add_argument("-f","--files",   help="The list of files that should be concatinated",
                                        type=str, nargs="+")
  
  parser.add_argument("-s", "--size",   help="Defines the maximum size of a single combined output file. Supports format ending such as 'MB' for megabytes, 'GB' for gigabytes. If nothing is specified then 'MB' is assumed.",
                                        type=str)

  parser.add_argument("--gpac",         help="Path to the GPAC install directory", 
                                        type=str)      
  
  parser.add_argument("-d", "--debug",  help="Prints out extra debugging information while script is running", 
                                        action="store_true")

  return parser.parse_args()


# If the script file is called by itself then execute the main function
if __name__ == '__main__':
  runMain()