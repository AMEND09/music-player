from flask import Flask, request, send_from_directory, render_template, Response
from indexer.indexer import index_music
from mutagen.mp3 import MP3
from ytms import MusicDownloader
import json
import os
import time
import threading

app = Flask(__name__)

BASE = os.path.dirname(__file__)
PLAYS_FILE = os.path.join(BASE, "indexes/plays.json")
DOWNLOADS = {}

os.makedirs(os.path.join(BASE, 'music'), exist_ok=True)
os.makedirs(os.path.join(BASE, 'indexes'), exist_ok=True)

try:
    with open(os.path.join(BASE, "indexes/tracks.json")) as f:
        text = f.read().strip()
        if text == "" or text == "[]":
            with open(os.path.join(BASE, "example_tracks.json")) as f2:
                TRACKS = json.load(f2)
            for track in TRACKS:
                if "filename" not in track:
                    track["filename"] = track["title"] + ".mp3"
        else:
            TRACKS = json.loads(text)
except:
    try:
        TRACKS = index_music()
    except:
        TRACKS = []

try:
    with open(PLAYS_FILE) as f:
        PLAYS = json.load(f)
except:
    PLAYS = {}


def save_plays():
    with open(PLAYS_FILE, "w") as f:
        json.dump(PLAYS, f, indent=2)


def find_track(id):
    for track in TRACKS:
        if track["id"] == int(id):
            return track
    return None


def artist_match(track_artist, name):
    if track_artist == name:
        return True
    parts = [p.strip() for p in track_artist.split(",")]
    return name in parts


def split_artists(track_artist):
    return [p.strip() for p in track_artist.split(",")]


def track_mtime(track):
    m = track.get("mtime", 0)
    if m:
        return m
    try:
        return os.path.getmtime(os.path.join(BASE, 'music', track["filename"]))
    except:
        return 0


def track_num(track):
    try:
        return int(str(track.get("track_number", "")).split("/")[0])
    except:
        return 999


def album_list():
    seen = {}
    for track in TRACKS:
        name = track["album"]
        if name not in seen:
            seen[name] = {"name": name, "parts": [], "count": 0, "added": 0, "art": "/art/album/" + name}
        seen[name]["count"] = seen[name]["count"] + 1
        m = track_mtime(track)
        if m > seen[name]["added"]:
            seen[name]["added"] = m
        for p in split_artists(track["artist"]):
            if p not in seen[name]["parts"]:
                seen[name]["parts"].append(p)
    out = []
    for a in seen.values():
        out.append({"name": a["name"], "artist": ", ".join(a["parts"]), "count": a["count"], "added": a["added"], "art": a["art"]})
    return sorted(out, key=lambda a: a["name"])


def album_plays(name):
    count = 0
    last = 0
    for track in TRACKS:
        if track["album"] == name:
            p = PLAYS.get(track["filename"])
            if p:
                count = count + p.get("count", 0)
                if p.get("last", 0) > last:
                    last = p["last"]
    return count, last


def download_job(job_id, item):
    global TRACKS
    try:
        md = MusicDownloader()
        def on_status(msg):
            DOWNLOADS[job_id]["message"] = msg
        md.download_item(item, download_path=os.path.join(BASE, 'music'), status_callback=on_status)
        TRACKS = index_music()
        DOWNLOADS[job_id] = {"id": job_id, "folder": item.get("title", ""), "status": "done", "message": "reindexed %d tracks" % len(TRACKS)}
    except Exception as e:
        DOWNLOADS[job_id] = {"id": job_id, "folder": item.get("title", ""), "status": "error", "message": str(e)[-500:]}


@app.route('/search', methods=['GET'])
def yt_search():
    q = request.args.get('q', '').strip()
    if q == '':
        return []
    try:
        md = MusicDownloader()
        res = md.search(q)
    except:
        return []
    items = []
    for a in res:
        if a.get("resultType") != "album":
            continue
        artists = a.get("artists", [])
        artist = artists[0].get("name", "") if artists else a.get("artist", "")
        thumbs = a.get("thumbnails", [])
        thumb = thumbs[-1]["url"] if thumbs else ""
        items.append({"resultType": "album", "browseId": a.get("browseId", ""),
            "title": a.get("title", ""), "artist": artist,
            "year": str(a.get("year", "")), "thumb": thumb, "data": a})
    return items


@app.route('/download', methods=['POST'])
def yt_download():
    data = request.get_json(force=True)
    item = data.get("data", data)
    if not item.get("browseId"):
        return "Missing album", 400
    job_id = str(len(DOWNLOADS) + 1)
    DOWNLOADS[job_id] = {"id": job_id, "folder": item.get("title", ""), "status": "downloading", "message": ""}
    t = threading.Thread(target=download_job, args=(job_id, item))
    t.daemon = True
    t.start()
    return {"job": job_id}


@app.route('/downloads', methods=['GET'])
def yt_status():
    return list(DOWNLOADS.values())


def get_art_bytes(filename):
    path = os.path.join(BASE, 'music', filename)
    audio = MP3(path)
    for key in audio.keys():
        if key.startswith('APIC'):
            pic = audio[key]
            return pic.mime, pic.data
    return None, None


@app.route('/', methods=['GET'])
def index():
    albums = album_list()
    added = sorted(albums, key=lambda a: a["added"], reverse=True)[:10]
    played = []
    for a in albums:
        count, last = album_plays(a["name"])
        if last > 0:
            b = dict(a)
            b["last"] = last
            b["plays"] = count
            played.append(b)
    recent = sorted(played, key=lambda a: a["last"], reverse=True)[:10]
    top = sorted(played, key=lambda a: a["plays"], reverse=True)[:10]
    return render_template('home.html', added=added, recent=recent, top=top)


@app.route('/album/<path:name>', methods=['GET'])
def album_page(name):
    found = []
    for track in TRACKS:
        if track["album"] == name:
            found.append(track)
    if not found:
        return "Not Available", 404
    found = sorted(found, key=track_num)
    parts = []
    for track in found:
        for p in split_artists(track["artist"]):
            if p not in parts:
                parts.append(p)
    return render_template('album.html', name=name, tracks=found, parts=parts)


@app.route('/artist/<path:name>', methods=['GET'])
def artist_page(name):
    found = []
    for track in TRACKS:
        if artist_match(track["artist"], name):
            found.append(track)
    if not found:
        return "Not Available", 404
    albums = {}
    for track in sorted(found, key=track_num):
        if track["album"] not in albums:
            albums[track["album"]] = []
        albums[track["album"]].append(track)
    return render_template('artist.html', name=name, albums=sorted(albums.items()))


@app.route('/tracks', methods=['GET'])
def tracks():
    if request.method == 'GET':
        return TRACKS
    else:
        return "Invalid Request"


@app.route('/tracks/<id>', methods=['GET'])
def return_track_by_id(id):
    track = find_track(id)
    if track:
        return track
    return "Not Available", 404


@app.route('/stream/<id>', methods=['GET'])
def stream_file_by_id(id):
    track = find_track(id)
    if not track:
        return "Not Available", 404
    return send_from_directory('music', track["filename"])


@app.route('/play/<id>', methods=['POST'])
def record_play(id):
    track = find_track(id)
    if not track:
        return "Not Available", 404
    key = track["filename"]
    entry = PLAYS.get(key, {"count": 0, "last": 0})
    entry["count"] = entry["count"] + 1
    entry["last"] = time.time()
    PLAYS[key] = entry
    save_plays()
    return {"count": entry["count"]}


@app.route('/reindex', methods=['POST'])
def reindex():
    global TRACKS
    TRACKS = index_music()
    return {"count": len(TRACKS)}


@app.route('/albums', methods=['GET'])
def albums():
    return album_list()


@app.route('/albums/<path:name>', methods=['GET'])
def albums_by_id(name):
    found = []
    for track in TRACKS:
        if track["album"] == name:
            found.append(track)
    if found:
        return found
    return "Not Available", 404


@app.route('/artists', methods=['GET'])
def artists():
    seen = {}
    for track in TRACKS:
        parts = [p.strip() for p in track["artist"].split(",")]
        for name in parts:
            if name not in seen:
                seen[name] = {"name": name, "tracks": 0, "albums": [], "art": "/art/artist/" + name}
            seen[name]["tracks"] = seen[name]["tracks"] + 1
            if track["album"] not in seen[name]["albums"]:
                seen[name]["albums"].append(track["album"])
    out = []
    for a in seen.values():
        out.append({"name": a["name"], "tracks": a["tracks"], "albums": len(a["albums"]), "art": a["art"]})
    return sorted(out, key=lambda a: a["name"])


@app.route('/artists/<path:name>', methods=['GET'])
def artists_by_id(name):
    found = []
    for track in TRACKS:
        if artist_match(track["artist"], name):
            found.append(track)
    if found:
        return found
    return "Not Available", 404


@app.route('/art/track/<id>', methods=['GET'])
def art_by_track(id):
    track = find_track(id)
    if not track:
        return "Not Available", 404
    mime, data = get_art_bytes(track["filename"])
    if not data:
        return "No Art", 404
    return Response(data, mimetype=mime)


@app.route('/art/album/<path:name>', methods=['GET'])
def art_by_album(name):
    for track in TRACKS:
        if track["album"] == name:
            mime, data = get_art_bytes(track["filename"])
            if data:
                return Response(data, mimetype=mime)
    return "No Art", 404


@app.route('/art/artist/<path:name>', methods=['GET'])
def art_by_artist(name):
    for track in TRACKS:
        if artist_match(track["artist"], name):
            mime, data = get_art_bytes(track["filename"])
            if data:
                return Response(data, mimetype=mime)
    return "No Art", 404


if __name__ == '__main__':
    app.run(debug=True, host="0.0.0.0", port=5001)
