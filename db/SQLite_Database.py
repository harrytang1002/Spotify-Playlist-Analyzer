import sqlite3
from spotify_api.Spotify_Client import getPlaylistTracks
from datetime import datetime

def getDBConnection():
    connection = sqlite3.connect('spotify_data.db')
    return connection

conn = getDBConnection()
conn.execute("PRAGMA foreign_keys = ON")

def initDB():
    with sqlite3.connect("spotify_data.db") as conn:
        cursor = conn.cursor()

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id TEXT PRIMARY KEY,
                display_name TEXT,
                email TEXT,
                access_token TEXT,
                refresh_token TEXT,
                token_expiration REAL
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usersPlaylists (
                playlist_id TEXT PRIMARY KEY,
                user_id TEXT,
                playlist_name TEXT,
                total_tracks INTEGER,
                FOREIGN KEY(user_id) REFERENCES users(user_id)
            );
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS playlistTracks (
                playlist_id TEXT PRIMARY KEY,
                track_id TEXT,
                track_name TEXT,
                artist_name TEXT,
                FOREIGN KEY(playlist_id) REFERENCES userPlaylists(playlist_id) ON DELETE CASCADE
            );
        """)

def storeUserInfo(userProfile, tokens):
    with sqlite3.connect("spotify_data.db") as conn:
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO users
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            userProfile["id"],
            userProfile.get("display_name"),
            userProfile.get("email"),
            tokens["access_token"],
            tokens["refresh_token"],
            tokens["token_expiration"]
        ))

def storePlaylistMetadata(userID, playlists):
    with sqlite3.connect("spotify_data.db") as conn:
        cursor = conn.cursor()
        for playlist in playlists:
            cursor.execute("""
                INSERT OR REPLACE INTO usersPlaylists
                VALUES (?, ?, ?, ?)
            """, (
                playlist["id"],
                userID,
                playlist["name"],
                playlist["tracks"]["total"]
            ))

def storePlaylistTracks(playlistID):
    tracks = getPlaylistTracks(playlistID)
    with sqlite3.connect("spotify_data.db") as conn:
        cursor = conn.cursor()
        for track in tracks:
            if track["track"] is None:
                continue
            cursor.execute("""
                INSERT OR REPLACE INTO playlistTracks
                VALUES (?, ?, ?, ?)
            """, (
                playlistID,
                track["track"]["id"],
                track["track"]["name"],
                track["track"]["artists"][0]["name"],
            ))

def getStoredTracks(playlistID):
    with sqlite3.connect("spotify_data.db") as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT track_name, artist_name FROM playlistTracks WHERE playlist_id = ?", (playlistID,))
        rows = cursor.fetchall()
        return [{"track": {"name": name, "artists": [{"name": artist}]}} for name, artist in rows]