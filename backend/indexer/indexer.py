from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
import os
import json


def read_tags(path):
    tags = EasyID3(path)
    audio = MP3(path)

    new_track = {
        "title": tags.get("title", ["Unknown"])[0],
        "artist": tags.get("artist", ["Unknown"])[0],
        "album": tags.get("album", ["Unknown"])[0],
        "track_number": tags.get("tracknumber", ["None"])[0],
        "duration_ms": int(audio.info.length * 1000),
    }

    return new_track


def index_music(music_dir="music", out_file="indexes/tracks.json"):
    base = os.path.dirname(os.path.dirname(__file__))
    music_path = os.path.join(base, music_dir)
    out_path = os.path.join(base, out_file)

    track_list = []

    id = 1
    for root, dirs, files in os.walk(music_path):
        dirs.sort()
        for file in sorted(files):
            if not file.lower().endswith(".mp3"):
                continue
            full = os.path.join(root, file)
            try:
                new_track = read_tags(full)
            except:
                continue
            new_track["id"] = id
            new_track["filename"] = os.path.relpath(full, music_path)
            new_track["mtime"] = os.path.getmtime(full)
            track_list.append(new_track)
            id = id + 1

    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(track_list, f, indent=2)

    return track_list


if __name__ == "__main__":
    tracks = index_music()
    print(tracks)
