import base64
import hashlib
import os
import secrets
from dotenv import load_dotenv
from flask import Flask, redirect, jsonify, request, session
from db.SQLite_Database import initDB, storeUserInfo, storePlaylistMetadata
from spotify_api.Spotify_Client import authURL, getAccessToken, getUserPlaylist, getPlaylistTracks, analyzePlaylistGenres, artistTopTracks

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

@app.route("/")
def index():
    return "Welcome to my Spotify App <a href = '/login'>Login with Spotify</a>"

@app.route("/login")
def login():
    session["code_verifier"] = secrets.token_urlsafe(64)
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(session["code_verifier"].encode("utf-8")).digest()
    ).rstrip(b'=').decode("utf-8")
    session["code_challenge"] = code_challenge
    return redirect(authURL())

@app.route("/callback")
def callback():
    if "error" in request.args:
        return jsonify({"error": request.args["error"]})

    if "code" in request.args:
        code = request.args["code"]
        getAccessToken(code)
    
    return redirect("/playlists")

@app.route("/playlists")
def playlists():
    userPlaylists = getUserPlaylist()
    playlistHTML = "<h1>Your Playlists:</h1><ul>"
    for playlist in userPlaylists:
        playlistHTML += f"<li><a href = '/analyze/{playlist['id']}'>{playlist['name']}</a></li>"
    playlistHTML += "</ul>"
    return playlistHTML

@app.route("/analyze/<playlistID>")
def analyze(playlistID):
    tracks = getPlaylistTracks(playlistID)
    sortedGenreMap, artistIDList = analyzePlaylistGenres(tracks)
    analysisHTML = "<h1>Top Genres in Playlist:</h1>"
    for i, (genre, data) in enumerate(sortedGenreMap.items(), start = 1):
        analysisHTML += f"<h3>{i}. {genre}</h3>"
        analysisHTML += "<p>Artists: " + ', '.join(artist[0] for artist in data[1:]) + "</p>"

    analysisHTML += "<h2>Select an Artist to View Top Tracks:</h2><ul>"
    for artist in artistIDList:
        analysisHTML += f'<li><a href="/artist/{artistIDList[artist]}">{artist}</a></li>'
    analysisHTML += "</ul>"
    return analysisHTML

@app.route("/artist/<artistID>")
def artistTracks(artistID):
    tracks = artistTopTracks(artistID)
    trackHTML = "<h1>Top Tracks:</h1><ul>"
    for i, track in enumerate(tracks, start = 1):
        trackHTML += f'<li>{i}. {track["name"]}</li>'
    trackHTML += "</ul>"
    return trackHTML

if __name__ == "__main__":
    app.run(debug = True)