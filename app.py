import base64
import hashlib
import os
import json
import secrets
import time
from collections import defaultdict
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask, redirect, jsonify, request, session
from requests import post, get
from urllib.parse import urlencode

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")
CLIENT_ID = os.getenv("CLIENT_ID")
CLIENT_SECRET = os.getenv("CLIENT_SECRET")
REDIRECT_URI = "https://spotify-playlist-analyzer-tgt7.onrender.com/callback"
AUTH_URL = "https://accounts.spotify.com/authorize"
SCOPE = "user-read-private user-read-email playlist-read-private"
CODE_VERIFIER = secrets.token_urlsafe(64)
CODE_CHALLENGE = base64.urlsafe_b64encode(
    hashlib.sha256(CODE_VERIFIER.encode("utf-8")).digest()
).rstrip(b'=').decode("utf-8")

def authURL():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "scope": SCOPE, 
        "redirect_uri": REDIRECT_URI,
        "code_challenge_method": "S256",
        "code_challenge": CODE_CHALLENGE
    }
    return f"{AUTH_URL}?{urlencode(params)}"

def getAccessToken(code):
    url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET,
        "code_verifier": CODE_VERIFIER
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    result = post(url, headers = headers, data = data)
    jsonResult = json.loads(result.content)
    session["access_token"] = jsonResult["access_token"]
    session["refresh_token"] = jsonResult["refresh_token"]
    session["token_expiration"] = datetime.now().timestamp() + jsonResult["expires_in"]

def refreshAccessToken():
    url = "https://accounts.spotify.com/api/token"
    data = {
        "grant_type": "refresh_token",
        "refresh_token": session["refresh_token"],
        "client_id": CLIENT_ID,
        "client_secret": CLIENT_SECRET
    }
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    result = post(url, headers = headers, data = data)
    jsonResult = json.loads(result.content)
    session["access_token"] = jsonResult["access_token"]
    session["token_expiration"] = datetime.now().timestamp() + jsonResult["expires_in"]

def checkTokenExp():
    if datetime.now().timestamp() > session["token_expiration"]:
        print("Token expired, refreshing...")
        refreshAccessToken()

def getAuthHeader():
    return {"Authorization" : "Bearer " + session["access_token"]}

def searchArtist(artistName):
    checkTokenExp()
    url = "https://api.spotify.com/v1/search"
    headers = getAuthHeader()
    query = f"?q={artistName}&type=artist&limit=1"
    queryUrl = url + query
    result = get(queryUrl, headers = headers)
    try:
        jsonResult = json.loads(result.content)["artists"]["items"]
    except KeyError:
        print("No artist exists with this name.")
        return None
    return jsonResult[0]

def getUserPlaylist():
    checkTokenExp()
    url = f"https://api.spotify.com/v1/me/playlists"
    headers = getAuthHeader()
    result = get(url, headers = headers)
    jsonResult = json.loads(result.content)["items"]
    return jsonResult

def getPlaylistTracks(playlistID):
    checkTokenExp()
    url = f"https://api.spotify.com/v1/playlists/{playlistID}/tracks"
    headers = getAuthHeader()
    query = f"?country=US&fields=items(track(name,id,artists(name,id)))"
    queryUrl = url + query
    result = get(queryUrl, headers = headers)
    jsonResult = json.loads(result.content)["items"]
    return jsonResult

def analyzePlaylistGenres(tracks):
    artistIDList = {}
    genreMap = defaultdict(lambda:[0])

    for track in tracks:
        artistID = track["track"]["artists"][0]["id"]
        artistGenre, artistName, artistPopularity = getArtistGenre(artistID)
        artistIDList[artistName] = artistID
        for genres in artistGenre:
            genreMap[genres][0] += 1
            if [artistName, artistPopularity] not in genreMap[genres]:
                genreMap[genres].append([artistName, artistPopularity])
    sortedGenreMap = topPlaylistGenres(genreMap)
    return sortedGenreMap, artistIDList

def getArtistGenre(artistID):
    checkTokenExp()
    url = f"https://api.spotify.com/v1/artists/{artistID}"
    headers = getAuthHeader()
    result = get(url, headers = headers)
    jsonResult = json.loads(result.content)
    return jsonResult["genres"], jsonResult["name"], jsonResult["popularity"]

def topPlaylistGenres(genreMap):
    sortedGenreMap = dict(
    (genre, [data[0]] + sorted(data[1:], key=lambda artist: artist[1], reverse=True))
    for genre, data in sorted(genreMap.items(), key=lambda item: item[1][0], reverse=True))
    return sortedGenreMap

def artistTopTracks(artistID):
    checkTokenExp()
    url = f"https://api.spotify.com/v1/artists/{artistID}/top-tracks"
    query = "?country=US"
    queryUrl = url + query
    headers = getAuthHeader()
    result = get(queryUrl, headers = headers)
    jsonResult = json.loads(result.content)["tracks"]
    return jsonResult


@app.route("/")
def index():
    return "Welcome to my Spotify App <a href = '/login'>Login with Spotify</a>"

@app.route("/login")
def login():
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