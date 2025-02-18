import base64
import os
import json
import time
from collections import defaultdict
from dotenv import load_dotenv
from requests import post, get

load_dotenv()

clientID = os.getenv("CLIENT_ID")
clientSecret = os.getenv("CLIENT_SECRET")
accessToken, tokenExpiration = None, 0


def getToken():
    global accessToken, tokenExpiration
    authString = clientID + ":" + clientSecret
    authBytes = authString.encode("utf-8")
    authBase64 = str(base64.b64encode(authBytes), "utf-8")
    url = "https://accounts.spotify.com/api/token"
    headers = {
        "Authorization" : "Basic " + authBase64,
        "Content-Type" : "application/x-www-form-urlencoded"
    }
    data = {"grant_type" : "client_credentials"}
    result = post(url, headers = headers, data = data)
    jsonResult = json.loads(result.content)
    accessToken = jsonResult["access_token"]
    tokenExp = jsonResult["expires_in"]
    tokenExpiration = time.time() + tokenExp

def checkTokenExp():
    if time.time() >= tokenExpiration:
        print("Token expired, refreshing...")
        getToken()

def getAuthHeader(token):
    return {"Authorization" : "Bearer " + token}

def searchArtist(artistName):
    checkTokenExp()
    url = "https://api.spotify.com/v1/search"
    headers = getAuthHeader(accessToken)
    query = f"?q={artistName}&type=artist&limit=1"
    queryUrl = url + query
    result = get(queryUrl, headers = headers)
    try:
        jsonResult = json.loads(result.content)["artists"]["items"]
    except KeyError:
        print("No artist exists with this name.")
        return None
    return jsonResult[0]

def getUserPlaylist(userID):
    checkTokenExp()
    url = f"https://api.spotify.com/v1/users/{userID}/playlists"
    headers = getAuthHeader(accessToken)
    result = get(url, headers = headers)
    jsonResult = json.loads(result.content)["items"]
    playlists = {}

    for i in range(len(jsonResult)):
        playlists[jsonResult[i]["name"]] = i
        playlists[str(i + 1)] = i
        print(f"{i + 1}. {jsonResult[i]["name"]}")
    selectedPlaylist = input("Which playlist would you like to analyze? (playlist name or number is fine): ")
    print()
    return jsonResult[playlists[selectedPlaylist]]

def getPlaylistTracks(playlistID):
    checkTokenExp()
    url = f"https://api.spotify.com/v1/playlists/{playlistID}/tracks"
    headers = getAuthHeader(accessToken)
    query = f"?country=US&fields=items(track(name,id,artists(name,id)))"
    queryUrl = url + query
    result = get(queryUrl, headers = headers)
    jsonResult = json.loads(result.content)["items"]
    artistIDList = {}
    genreMap = defaultdict(lambda:[0])

    for i in range(len(jsonResult)):
        print(f"{i + 1}. {jsonResult[i]["track"]["name"]} - {', '.join(d["name"] for d in jsonResult[i]["track"]["artists"])}")
        artistID = jsonResult[i]["track"]["artists"][0]["id"]
        artistGenre, artistName, artistPopularity = getArtistGenre(artistID)
        artistIDList[artistName] = artistID
        for genres in artistGenre:
            genreMap[genres][0] += 1
            if [artistName, artistPopularity] not in genreMap[genres]:
                genreMap[genres].append([artistName, artistPopularity])
    topPlaylistGenres(genreMap, artistIDList)

def getArtistGenre(artistID):
    checkTokenExp()
    url = f"https://api.spotify.com/v1/artists/{artistID}"
    headers = getAuthHeader(accessToken)
    result = get(url, headers = headers)
    genresResult = json.loads(result.content)["genres"]
    nameResult = json.loads(result.content)["name"]
    popularityResult = json.loads(result.content)["popularity"]
    return genresResult, nameResult, popularityResult

def topPlaylistGenres(genreMap, artistIDList):
    sortedGenreMap = dict(
    (genre, [data[0]] + sorted(data[1:], key=lambda artist: artist[1], reverse=True))
    for genre, data in sorted(genreMap.items(), key=lambda item: item[1][0], reverse=True))

    # show users all the genres in their playlist
    # print(', '.join(genre for genre in list(sortedGenreMap.keys())))

    top5Genres = list(sortedGenreMap.keys())[:5]
    print()
    print("Top 5 Genres in Your Playlist:")
    for i in range(len(top5Genres)):
        print(f"{i + 1}. {top5Genres[i]}")
        print(', '.join(artist[0] for artist in sortedGenreMap[top5Genres[i]][1:]))
        print()
    while True:
        selectedArtist = input("Please enter an artist's name if you would like to view their top tracks (or type 'q' to stop): ")
        if selectedArtist.lower() == "q":
            break
        try:
            songs = artistTopTracks(artistIDList[selectedArtist])
            for i, song in enumerate(songs):
                print(f"{i + 1}. {song["name"]}")
        except KeyError:
            print("Invalid artist name. Please enter the artist's name as shown and try again.")


def artistTopTracks(artistID):
    checkTokenExp()
    url = f"https://api.spotify.com/v1/artists/{artistID}/top-tracks"
    query = "?country=US"
    queryUrl = url + query
    headers = getAuthHeader(accessToken)
    result = get(queryUrl, headers = headers)
    jsonResult = json.loads(result.content)["tracks"]
    return jsonResult
    
    
getToken()
playlist = getUserPlaylist("31rc7w4va23j5qxdex27ikg5klve")
getPlaylistTracks(playlist["id"])


