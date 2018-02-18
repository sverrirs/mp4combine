#!/usr/bin/env python
# coding=utf-8
__version__ = "2.2.0"
# When modifying remember to issue a new tag command in git before committing, then push the new tag
#   git tag -a v2.2.0 -m "v2.2.0"
#   git push origin --tags
"""
Python script that generates the necessary mp4box -cat commands to concatinate multiple video files 
together and generates a chapter file that marks the beginning of each concatenated file in the final result.

This script requires the GPAC package to be installed with the mp4box command line utility.
https://gpac.wp.mines-telecom.fr/downloads/

The script is written in Python 3.5

Details about Xbox video formats:
https://support.xbox.com/en-IE/xbox-360/console/audio-video-playback-faq

Requires:
  pip install humanize
  pip install colorama
  pip install termcolor

  pip install -r requirements.txt

See: https://github.com/sverrirs/mp4combine
Author: Sverrir Sigmundarson  info@sverrirs.com  https://www.sverrirs.com
"""

from colorama import init, deinit # For colorized output to console windows (platform and shell independent)
from constant import DISKSIZES, ABSSIZES, Colors # Constants for the script

import humanize # Display human readible values for sizes etc
import sys, os, time
from pathlib import Path # to check for file existence in the file system
import argparse # Command-line argument parser
import ntpath # Used to extract file name from path for all platforms http://stackoverflow.com/a/8384788
import glob # Used to do partial file path matching when listing file directories in search of files to concatinate http://stackoverflow.com/a/2225582/779521
import subprocess # To execute shell commands 
import re # To perform substring matching on the output of mp4box and other subprocesses
from datetime import timedelta # To store the parsed duration of files and calculate the accumulated duration
from random import shuffle # To be able to shuffle the list of files if the user requests it
#
# Provides natural string sorting (numbers inside strings are sorted in the correct order)
# http://stackoverflow.com/a/3033342/779521
def natural_key(string_):
  """See http://www.codinghorror.com/blog/archives/001018.html"""
  return [int(s) if s.isdigit() else s for s in re.split(r'(\d+)', string_)]

#
# The main entry point for the script
def runMain():
  try:
    init() # Initialize the colorama library

    # Compile the regular expressions
    regex_mp4box_duration = re.compile(r"Computed Duration (?P<hrs>[0-9]{2}):(?P<min>[0-9]{2}):(?P<sec>[0-9]{2}).(?P<msec>[0-9]{3})", re.MULTILINE)

    # Construct the argument parser for the commandline
    args = parseArguments()

    # Get the current working directory (place that the script is executing from)
    working_dir = sys.path[0]

    # Get the mp4box exec
    mp4exec = findMp4Box(args.gpac, working_dir)

    # Get ffmpeg exec
    ffmpegexec = findffmpeg(args.ffmpeg, working_dir)

    # Detect the maximum file size that should be generated in kilobytes, if <=0 then unlimited
    max_out_size_kb = determineMaximumOutputfileSizeInKb(args.size, args.disk)

    # Create the output file names both for the video file and the intermediate chapters file
    path_out_file = Path(args.output)
    path_chapters_file = path_out_file.with_suffix('.txt') # Just change the file-extension of the output file to TXT

    # If the output files exist then either error or overwrite
    if( path_out_file.exists() ):
      if( args.overwrite ):
        os.remove(str(path_out_file))
      else:
        print( "Output file '{0}' already exists. Use --overwrite switch to overwrite.".format(Colors.filename(path_out_file.name)))
        sys.exit(0)

    # Get all the input files
    in_files = getFileNamesFromGrepMatch(args.match, path_out_file)
    if( in_files is None ):
      print( "No mp4 video files found matching '{0}'".format(args.match))
      sys.exit(0)

    file_infos = []
    # Only process files that have file-ending .mp4 and not files that have the same name as the joined one
    for in_file in in_files:
      print("File: {0}".format(Colors.filename(in_file)))
      file_infos.append(parseMp4boxMediaInfo(in_file, mp4exec, regex_mp4box_duration))

    # If nothing was found then don't continue, this can happen if no mp4 files are found or if only the joined file is found
    if( len(file_infos) <= 0 ):
      print( "No mp4 video files found matching '{0}'".format(args.match))
      sys.exit(0)

    print("Found {0} files".format(len(file_infos)))

    # If the user wants the list of files shuffled then do that now in place
    if( args.shuffle ):
      shuffle(file_infos)
      print("File list shuffled")

    # Now create the list of files to create
    video_files = []
    chapters = []
    cumulative_dur = timedelta(seconds=0)
    cumulative_size = 0
    # Collect the file info data and chapter points for all files
    for file_info in file_infos:
      video_files.append(file_info['file'])
      chapters.append({"name": Path(file_info['file']).stem, "timecode":formatTimedelta(cumulative_dur)})
      cumulative_dur += file_info['dur'] # Count the cumulative duration
      cumulative_size += file_info['size'] 
     
    createCombinedVideoFile(video_files, chapters, cumulative_dur, cumulative_size, mp4exec, ffmpegexec, path_out_file, path_chapters_file, args.overwrite, args.videosize, max_out_size_kb )
    
    print(Colors.success("Script completed successfully, bye!"))
  finally:
    deinit() #Deinitialize the colorama library

#
# Creates a combined video file for a segment
def createCombinedVideoFile(video_files, chapters, cumulative_dur, cumulative_size, mp4exec, ffmpegexec, path_out_file, path_chapters_file, args_overwrite, args_videomaxsize, max_out_size_kb=0 ):

  print( "Output: {0}".format(Colors.fileout(str(path_out_file))))
  
  # Add the final chapter as the end for this segment
  chapters.append({"name": "End", "timecode":formatTimedelta(cumulative_dur)})

  # Chapters should be +1 more than files as we have an extra chapter ending at the very end of the file
  print("{0} chapters, {1} running time, {2} total size".format( len(chapters), formatTimedelta(cumulative_dur), humanize.naturalsize(cumulative_size, gnu=True)))

  # Write the chapters file to out
  saveChaptersFile(chapters, path_chapters_file)

  # Re-encode and combine the video files first
  print(Colors.toolpath("Combining and re-encoding video files (ffmpeg), this will take a while..."))
  reencodeAndCombineVideoFiles(ffmpegexec, video_files, path_out_file, args_videomaxsize)
  
  # Now create the combined file and include the chapter marks
  print(Colors.toolpath("Adding chapters to combined video file (mp4box)"))
  addChaptersToVideoFile(mp4exec, path_out_file, path_chapters_file)

  # Delete the chapters file
  os.remove(str(path_chapters_file))

  # Read the created file to learn its final filesize
  size_out_file_kb = os.path.getsize(str(path_out_file)) / 1024
  print( Colors.toolpath("Final size of video file is: {0}".format(humanize.naturalsize(size_out_file_kb * 1024))))

  # Now split the file if requested
  if max_out_size_kb > 0 and size_out_file_kb > max_out_size_kb :
    print( Colors.toolpath("Size limit exceeded, splitting video into files of max size: {0}".format(humanize.naturalsize(max_out_size_kb * 1000))))
    splitVideoFile(mp4exec, path_out_file, max_out_size_kb)

#
# Attempts to detect the requested size of the output file based on the input parameters
# the absolute_size is overridden by disk_capacity if both are specified
# Returns KB (kilobytes)
def determineMaximumOutputfileSizeInKb(absolute_size, disk_capacity):
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
    return total_size / 1000 # Return kilobytes but in the metric system sense not the "1024 byte sense"
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
def findMp4Box(path_to_gpac_install=None, working_dir=None):
  
  if( not path_to_gpac_install is None and os.path.isfile(os.path.join(path_to_gpac_install, "mp4box.exe")) ):
    return os.path.join(path_to_gpac_install, "mp4box.exe")

  # Attempts to search for it under the bin folder
  bin_dist = os.path.join(working_dir, "..\\bin\\GPAC\\mp4box.exe")
  if( os.path.isfile(bin_dist)):
    return str(Path(bin_dist).resolve())
  
  # Attempts to search for it under C:\Program Files\GPAC
  if( os.path.isfile("C:\\Program Files\\GPAC\\mp4box.exe")):
    return "C:\\Program Files\\GPAC\\mp4box.exe"
  
  # For 32 bit installs
  if( os.path.isfile("C:\\Program Files\\GPAC\\mp4box.exe")):
    return "C:\\Program Files (x86)\\GPAC\\mp4box.exe"
  
  # Throw an error
  raise ValueError('Could not locate GPAC install, please use the --gpac switch to specify the path to the mp4box.exe file on your system.')

#
# Locates the ffmpeg executable and returns a full path to it
def findffmpeg(path_to_ffmpeg_install=None, working_dir=None):
  if( not path_to_ffmpeg_install is None and os.path.isfile(os.path.join(path_to_ffmpeg_install, "ffmpeg.exe")) ):
    return os.path.join(path_to_ffmpeg_install, "ffmpeg.exe")

  # Attempts to search for it under the bin folder
  bin_dist = os.path.join(working_dir, "..\\bin\\ff\\ffmpeg.exe")
  if( os.path.isfile(bin_dist)):
    return str(Path(bin_dist).resolve())
  
  # Throw an error
  raise ValueError('Could not locate FFMPEG install, please use the --ffmpeg switch to specify the path to the ffmpeg.exe file on your system.')

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
# Executes FFMPEG for all video files to be joined and reencodes
def reencodeAndCombineVideoFiles(ffmpeg_path, video_files, path_out_file, args_videomaxsize ):
  # Construct the args to ffmpeg
  # See https://stackoverflow.com/a/26366762/779521
  prog_args = [ffmpeg_path]

  # How many video files
  video_count = len(video_files)

  # The filter complex configuration
  filter_complex_concat = []
  filter_complex_scale = []
  curr_video = 0
   
  # -filter_complex 
  # "[0:v]scale=1024:576:force_original_aspect_ratio=1[v0]; 
  # [1:v]scale=1024:576:force_original_aspect_ratio=1[v1]; 
  # [v0][0:a][v1][1:a]concat=n=2:v=1:a=1[v][a]" 

  # For every input construct their filter complex to be added later
  # Force scaling of videos first 
  for video_file in video_files:
    prog_args.append("-i")
    prog_args.append(str(Path(video_file)))  # Don't surrount with quotes ""

    # Add the scaling instructions for the input video and give it a new output
    # Force downscaling of aspect ratio and size to the minimal available
    # the value of =1 is the same as ‘decrease’ => The output video dimensions will automatically be decreased if needed.
    filter_complex_scale.append("[{0}:v]scale={1}:force_original_aspect_ratio=1[v{0}];".format(curr_video, args_videomaxsize))

    # Add concat filter with the video output from the scaling and audio index from the original video
    filter_complex_concat.append("[v{0}]".format(curr_video))
    filter_complex_concat.append("[{0}:a]".format(curr_video))
    curr_video += 1

  # Add the final part of the concat filter
  filter_complex_concat.append("concat=n={0}:v=1:a=1".format(video_count))
  filter_complex_concat.append("[v]")
  filter_complex_concat.append("[a]")

  # Join and add the filter complex to the args
  # First the scaling then the concats
  prog_args.append("-filter_complex")
  prog_args.append("".join(filter_complex_scale) + "".join(filter_complex_concat)) # Don't surrount with quotes ""

  # The mapping for the video and audio
  prog_args.append("-map")
  prog_args.append("[v]")
  prog_args.append("-map")
  prog_args.append("[a]")

   # Don't show copyright header
  prog_args.append("-hide_banner")

  # Don't show excess logging (only things that cause the exe to terminate)
  prog_args.append("-loglevel")
  prog_args.append("verbose") 
  
  # Force showing progress indicator text
  prog_args.append("-stats") 

  # Overwrite any prompts with YES
  prog_args.append("-y")  

  # Finally the output file
  prog_args.append(str(path_out_file))  # Don't surrount with quotes ""

  # Disable colour output from FFMPEG before we start
  os.environ['AV_LOG_FORCE_NOCOLOR'] = "1"

  # Run ffmpeg and wait for the output file to be created before returning
  return _runSubProcess(prog_args, path_to_wait_on=path_out_file)

#
# Calls mp4box to create the concatinated video file and includes the chapter file as well
def addChaptersToVideoFile(mp4box_path, path_video_file, path_chapters_file):

  # Check to see if the video file exists before doing anything
  if not path_video_file.exists():
    raise ValueError("Video file {0} could not be found. No chapters were added.".format(path_video_file))

  # Construct the args to mp4box
  prog_args = [mp4box_path]

  # Overwrite the default temporary folder to somewhere we
  # know that the current user has write privileges
  prog_args.append("-tmp")
  prog_args.append("{0}".format(os.environ['TMP']))

  # Add the chapter file
  prog_args.append("-add")
  prog_args.append(str(path_chapters_file)+":chap")

  # Add the output file at the very end, we will add the
  # chapter marks in-place
  prog_args.append(str(path_video_file))

  # Run the command
  return _runSubProcess(prog_args)

#
# Splits an existing video file into requested chunks
def splitVideoFile(mp4box_path, path_video_file, max_out_size_kb):
  
  # Can't split something that doesn't exist
  if not path_video_file.exists():
    raise ValueError("Video file {0} could not be found. Nothing was split.".format(path_video_file))

  # Construct the args to mp4box
  prog_args = [mp4box_path]

  # Specify the maximum split size
  prog_args.append("-splits")
  prog_args.append(str(max_out_size_kb))

  # Overwrite the default temporary folder to somewhere we
  # know that the current user has write privileges
  prog_args.append("-tmp")
  prog_args.append("{0}".format(os.environ['TMP']))

  # Add the input file we want to split
  prog_args.append(str(path_video_file))

  # Specify the same file again as an out parameter to use the same directory
  prog_args.append("-out")
  prog_args.append(str(path_video_file))

  # Run the command
  return _runSubProcess(prog_args)


# Runs a subprocess using the arguments passed and monitors its progress while printing out the latest
# log line to the console on a single line
def _runSubProcess(prog_args, path_to_wait_on=None):

  # Force a UTF8 environment for the subprocess so that files with non-ascii characters are read correctly
  # for this to work we must not use the universal line endings parameter
  my_env = os.environ
  my_env['PYTHONIOENCODING'] = 'utf-8'

  retcode = None

  # Run the app and collect the output
  ret = subprocess.Popen(prog_args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True, env=my_env)
  try:
    longest_line = 0
    trace_lines = []
    while True:
      try:
        #line = ret.stdout.readline().decode('utf-8')
        line = ret.stdout.readline()
        if not line:
          break
        line = line.strip()[:80] # Limit the max length of the line, otherwise it will screw up our console window
        trace_lines.append(line)
        longest_line = max( longest_line, len(line))
        sys.stdout.write('\r '+line.ljust(longest_line))
        sys.stdout.flush()
      except UnicodeDecodeError:
        continue # Ignore all unicode errors, don't care!

    # Ensure that the return code was ok before continuing
    retcode = ret.poll()
    while retcode is None:
      retcode = ret.poll()
  except KeyboardInterrupt:
    ret.terminate()
    raise

  # Move the input to the beginning of the line again
  # subsequent output text will look nicer :)
  sys.stdout.write('\r '+"Done!".ljust(longest_line))
  print()

  if( retcode != 0 ): 
    print( "Error while executing {0}".format(prog_args[0]))
    print(" Full arguments:")
    print( " ".join(prog_args))
    print( "Full error")
    print("\n".join(trace_lines))
    raise ValueError("Error {1} while executing {0}".format(prog_args[0], retcode))

  # If we should wait on the creation of a particular file then do that now
  total_wait_sec = 0
  if not path_to_wait_on is None and not path_to_wait_on.is_dir():
    while not path_to_wait_on.exists() or total_wait_sec < 5:
      time.sleep(1)
      total_wait_sec += 1

    if not path_to_wait_on.exists() or not path_to_wait_on.is_file() :
      raise ValueError("Expecting file {0} to be created but it wasn't, something went wrong!".format(str(path_to_wait_on)))
  return retcode


def parseArguments():
  parser = argparse.ArgumentParser()
  
  parser.add_argument("-o", "--output", help="The path and filename of the concatenated output file. If multiple files then the script will append a number to the filename.",
                                        type=str)

  parser.add_argument("-m","--match",   help="A grep style match that should be used to detect files to concatinate.",
                                        type=str)                                        
  
  parser.add_argument('--disk',          help="When defined this defines the maximum file size to generate so that they will fit the required optical disk capacity. dvd4=4.7GB, dvd8=8.5GB, br25=25GB. If specified this overrides the -s/--size argument.",
                                        choices=['dvd4', 'dvd8', 'br25'])

  parser.add_argument("-s", "--size",   help="Defines the maximum size of a single combined output file. Supports format ending such as 'MB' for megabytes, 'GB' for gigabytes. If nothing is specified then 'MB' is assumed. Overridden by the --disk argument if both are specified. Supports only numbers using dot (.) as decimal separator, e.g. '15.5GB'", type=str)

  parser.add_argument("--gpac",         help="Path to the GPAC install directory (not including the exe)", 
                                        type=str)

  parser.add_argument("--ffmpeg",       help="Path to the ffmpeg install directory (not including the exe)", 
                                        type=str)

  parser.add_argument("--videosize",    help="The desired maximum w/h size for the output video, default is 1024:576 (in case of multiple sizes for videos then all videos above this size are downsized to match) Aspect ratios will be downscaled as needed.", 
                                        default="1024:576",
                                        type=str)

  parser.add_argument("--overwrite",    help="Existing files with the same name as the output will be silently overwritten.", 
                                        action="store_true")

  parser.add_argument("--shuffle",     help="Shuffles the list of episodes in a random fashion before combining. Useful to generate a random list of episodes to fill a DVD.", 
                                        action="store_true")
  
  parser.add_argument("-d", "--debug",  help="Prints out extra debugging information while script is running", 
                                        action="store_true")


  return parser.parse_args()


# If the script file is called by itself then execute the main function
if __name__ == '__main__':
  runMain()