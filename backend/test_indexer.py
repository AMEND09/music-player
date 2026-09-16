from mutagen.easyid3 import EasyID3 
from mutagen.mp3 import MP3
import os
import json
import sqlite3

  
track_dictionary = {}

def read_tags(path):
    tags = EasyID3(path)
    audio = MP3(path)

    new_track= {
        "title": tags.get("title", ["Unknown"])[0],
        "artist_names": tags.get("artist", ["Unknown"])[0],
        "album_name": tags.get("album", ["Unknown"])[0],
        "track_number": tags.get("tracknumber", ["None"])[0],
        "duration_ms": int(audio.info.length * 1000),
    }

    return new_track

with open("indexes/tracks.json", "r+") as f:
    files = os.listdir('music')
    for track in files:
        new_track = read_tags('music/' + track)
        track_dictionary[track] = new_track
    json.dumps(track_dictionary)

print(read_tags("music/Testify.mp3"))
