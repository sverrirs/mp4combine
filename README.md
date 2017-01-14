# Mp4 Video Joiner

Python script that assist in concatenating mp4 video files into a single larger file and automatically create named chapter marks at each join making it really easy to skip forward and backwards within the video file.

The script relies on the `mp4box` utility from the [GPAC](https://gpac.wp.mines-telecom.fr/downloads/) software bundle You will need to download and install this bundle first before using this tool. 

> Currently this script has only been developed for use on Windows but I welcome any and all pull requests. So if you feel you can improve the OS compatability I'd appreciate your help.

This script solves long outstanding feature requests for the GPAC toolkit such as [#325](https://sourceforge.net/p/gpac/bugs/325/)

:heart:

## Requires

Python 3.x

```
pip install humanize
```

## Simple usage
Assuming you have a bunch of videos named "clipXX.mp4" in a folder called _videos_ then this is how you feed all of them into the concatinator and specify an output file

```
python catgen.py --match "D:\videos\clip*" -o "D:\videos\all_clips.mp4"
```

## Advanced usage

Assuming you have a large 16GB list of [Barbie](https://en.wikipedia.org/wiki/Barbie:_Life_in_the_Dreamhouse) Mp4 video files in a folder. Now you'd like to burn them all to a DVD to play on your XBox or Playstation computer. However the list of files is much greater than what can fit on a single DVD disk.

No worries! :relieved:

The script can automatically segment the output files according to known DVD and BluRay disk sizes using the `--disk` command line argument

```
python catgen.py --match "D:\barbie\*.mp4" -o "D:\toburn\Barbie.mp4" --disk dvd8
```

This will create multiple output files
```
Output: D:\toburn\Barbie_001.mp4
23 chapters, 08:32:15.560 running time, 7.6G total size

Output: D:\toburn\Barbie_002.mp4
23 chapters, 08:32:04.720 running time, 7.6G total size

Output: D:\toburn\Barbie_003.mp4
5 chapters, 01:33:07.920 running time, 1.4G total size
```

Now you can burn each individual file to a dvd. 

_Neat_ :thumbsup:

> The disk settings supported are `dvd4` (4.7GB), `dvd8` (8.5GB) and `br25` (25GB).

You can also specify a custom file size using the `--size` argument. The example below limits the output file size to 800MB.

```
python catgen.py -m "D:\barbie\*.mp4" -o "D:\toburn\Barbie.mp4" --size 800MB
```

The `--size` argument supports multiple format endings such as 'MB' for megabytes and 'GB' for gigabytes. If nothing is specified then 'MB' is assumed. You can also specify fractional sizes such as '15.5GB'.

## Overwriting existing files
If the output file exists the script will by default print an error and terminate without doing anything. To silently overwrite existing files with the same file name you can use the `--overwrite` switch

```
python catgen.py -m "D:\barbie\*.mp4" -o "D:\toburn\Barbie.mp4" --disk dvd8 --overwrite
```

## Contributing

I welcome any and all suggestions and fixes either through the issue system above or through pull-requests.

Although this project is small it has a [code of conduct](CODE_OF_CONDUCT.md) that I hope everyone will do their best to follow when contributing to any aspects of this project. Be it discussions, issue reporting, documentation or programming. 

If you don't want to open issues here on Github, send me your feedback by email at [mp4cat@sverrirs.com](mailto:mp4cat@sverrirs.com).

> _"Be excellent to each other"_
> :hatched_chick: