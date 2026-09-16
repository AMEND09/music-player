from flask import Flask, request, send_from_directory
import json

with open("example_tracks.json") as f:
    TRACKS = json.load(f)

app = Flask(__name__)

@app.route('/tracks', methods=['GET'])
def tracks():
    if request.method == 'GET':
        return TRACKS
    else:
        return "Invalid Request"
@app.route('/tracks/<id>', methods=['GET'])
def return_track_by_id(id):
    for track in TRACKS:
        if track["id"] == int(id):
            return track
    return "Not Available"

@app.route('/stream/<id>', methods=['GET'])
def stream_file_by_id(id):
    return send_from_directory('music', return_track_by_id(id)["title"] + ".mp3")

if __name__ == '__main__':
    app.run()


