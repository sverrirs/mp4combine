# Mp4 Video Combiner

Python script that assist in concatenating mp4 video files into a single larger file and automatically create named chapter marks at each join making it really easy to skip forward and backwards within the video file. 

All video files created by this tool are fully compatible and play without errors on Xbox 360/One, PS4 and all major video players on desktop or mobile.

The script relies on the `mp4box` utility from the [GPAC](https://gpac.wp.mines-telecom.fr/downloads/) software bundle and the `ffmpeg` utility from [ffmpeg.org](https://www.ffmpeg.org/). The Windows 64bit version of both these tools are included in the bundle.

> Currently this script has only been developed for use on Windows but I welcome any and all pull requests. So if you feel you can improve the OS compatability I'd appreciate your help.

This script solves long outstanding feature requests for the GPAC toolkit such as [#325](https://sourceforge.net/p/gpac/bugs/325/)

Details and discussions can also be found on [my blog](https://blog.sverrirs.com/2017/01/joining-mp4-files-with-chapters.html).

:heart:

- [Requires](#requires)
- [Simple usage](#simple-usage)
- [Advanced usage](#advanced-usage)
  - [Handling input videos of different sizes](#handling-input-videos-of-different-sizes)
  - [Overwriting existing files](#overwriting-existing-files)
  - [Shuffling the list of files](#shuffling-the-list-of-files)
  - [Providing a cut point file as an input](#providing-a-cut-point-file-as-an-input)
  - [Merging videos containing soft subtitles](#merging-videos-containing-soft-subtitles)
  - [Disabling audio in output video](#disabling-audio-in-output-video)
- [Contributing](#contributing)

## Requires

Python 3.5+

Before first use make sure you install all requirements using 

```
pip install -r requirements.txt
```


## Simple usage
Assuming you have a bunch of videos named "clipXX.mp4" in a folder called _videos_ then this is how you feed all of them into script and have it automagically combine all the files and place nice chapter marks at the seams.

```
python combine.py --match "D:\videos\clip*" -o "D:\videos\all_clips.mp4"
```

## Advanced usage

> For all options supported by this tool run `python combine.py -h`

Assuming you have a large 16GB list of [Barbie](https://en.wikipedia.org/wiki/Barbie:_Life_in_the_Dreamhouse) Mp4 video files in a folder. Now you'd like to burn them all to a DVD to play on your XBox or Playstation computer. However the list of files is much greater than what can fit on a single DVD disk.

No worries! :relieved:

The script can automatically segment the output files according to known DVD and BluRay disk sizes using the `--disk` command line argument

```
python combine.py --match "D:\barbie\*.mp4" -o "D:\toburn\Barbie.mp4" --disk dvd8
```

This will create the original output file and then also split files based on your maximum size
```
D:\toburn\Barbie.mp4
D:\toburn\Barbie_001.mp4
D:\toburn\Barbie_002.mp4
D:\toburn\Barbie_003.mp4
```

Now you can burn each individual split file to a dvd. 

_Neat_ :thumbsup:

> The disk settings supported are `dvd4` (4.7GB), `dvd8` (8.5GB) and `br25` (25GB).

You can also specify a custom file size using the `--size` argument. The example below limits the output file size to 800MB.

```
python combine.py -m "D:\barbie\*.mp4" -o "D:\toburn\Barbie.mp4" --size 800MB
```

The `--size` argument supports multiple format endings such as 'MB' for megabytes and 'GB' for gigabytes. If nothing is specified then 'MB' is assumed. You can also specify fractional sizes such as '15.5GB'.

> If you intend to play the files on your Xbox console then you need to limit the file size to be no more than `4GB`. This file limit is imposed by the FAT32 file system (see [Q12](http://support.xbox.com/en-US/xbox-360/console/audio-video-playback-faq#Q11)).

## Handling input videos of different sizes
If the input videos are not of the same width or height then the script will automatically attempt to scale all of the source material to `1024x576` resolution. This scaling size can be configured using the `--videosize` parameter.

Below is a command that forces a `1280 x 720` HD resolution for all input files. Files with smaller resolution will be upscaled and those with larger resolutions will be downscaled.

```
python combine.py -m "D:\barbie\*.mp4" -o "D:\toburn\Barbie.mp4" --videosize "1280:720"
```

> Ensure you separate the dimensions with the colon character `:`

## Overwriting existing files
If the output file exists the script will by default print an error and terminate without doing anything. To silently overwrite existing files with the same file name you can use the `--overwrite` switch

```
python combine.py -m "D:\barbie\*.mp4" -o "D:\toburn\Barbie.mp4" --disk dvd8 --overwrite
```

## Shuffling the list of files
By default the files are concatinated in order by their filename. In case you want to randomize their order (e.g. if you're creating a shuffled playlist type of file) you can use the `--shuffle` argument

```
python combine.py -m "D:\videos\*.mp4" -o "D:\toburn\Shuffle.mp4" --disk dvd4 --shuffle
```

## Providing a cut point file as an input
The script can cut beginning and endings of files automatically if a cut point file is provided using the `--cuts` or `-c` argument.

The file format is simple comma separated file on the form
```
FILE_NAME_WITH_EXTENSION, START_TIME_CODE, END_TIME_CODE
```

Example cuts file (cutinfo.txt)
```
Barbie1.mp4, 00:33, 01:01
Barbie2.mp4, 00:50, 1:45
```

Then to perform the cuts, run the following command

```
python combine.py -m "D:\barbie\*.mp4" -o "D:\toburn\Barbie.mp4" --cuts "D:\toburn\cutinfo.txt"
```

Will produce an output file (Barbie.mp4) of total 1:23 duration where the first 28 seconds are from Barbie1.mp4 and the remaining 55 seconds are from Barbie2.

## Merging videos containing soft subtitles
When merging videos containing subtitle tracks then the `--burnsubs` option can be specified so that the resulting combined file will have the default subtitle track embedded in the video. 

> It is not currently possible to merge soft subtitles (subtitles on separate tracks).

## Disabling audio in output video
By default the script will attempt to merge both video and audio tracks from the source videos. If one or more of the source videos have no audio tracks then the script will fail with an error similar to

```
Stream specifier ':a' in filtergraph description .... matches no streams.
```

You can use the `--noaudio` switch to force the script to skip all audio tracks from the source videos and only produce an output video of the merged video tracks.

The below example will produce a completely silent video file

```
python combine.py --match "D:\barbie\*.mp4" -o "D:\toburn\Barbie_silent.mp4" --noaudio
```

## Contributing

I welcome any and all suggestions and fixes either through the issue system above or through pull-requests.

Although this project is small it has a [code of conduct](CODE_OF_CONDUCT.md) that I hope everyone will do their best to follow when contributing to any aspects of this project. Be it discussions, issue reporting, documentation or programming. 

If you don't want to open issues here on Github, send me your feedback by email at [mp4combine@sverrirs.com](mailto:mp4combine@sverrirs.com).

> _"Be excellent to each other"_
> :hatched_chick: