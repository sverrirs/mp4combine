# Mp4box Concatination Helper

Assists in concatenating files using the `mp4box` utility. 
The tool creates a chapter file for all concatenated files and the resulting joined file will have chapter marks at the joining points.

## Usage
Assuming you have a bunch of videos named "clipsXX.mp4" in a folder called _videos_ then this is how you feed all of them into the concatinator and specify an output file

```
python catgen.py -m "D:\videos\clips*" -o "D:\videos\all_clips.mp4"
```

