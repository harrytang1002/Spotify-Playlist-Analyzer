import sqlite3
from datetime import datetime

def getDBConnection():
    connection = sqlite3.connect('spotify_data.db')
    return connection

conn = getDBConnection()

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