from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, redirect, url_for, session, request
import urllib.parse

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    return 'Hello, World! <a href="/login">Login</a>'

@app.route('/callback')
def callback():
    code = request.args.get('code')
    if code:
        sp_oauth = spotipy.oauth2.SpotifyOAuth(client_id, client_secret, redirect_uri, scope='user-library-read playlist-read-private', cache_path=".cache")
        token_info = sp_oauth.get_access_token(code)

        # Save the token in the session for later use
        session['token_info'] = token_info

        return 'Callback successful! You can now retrieve playlists. <a href="/get_playlists">Get Playlists</a>'
    else:
        return 'Error during callback'

@app.route('/login')
def login():
    scope = 'user-library-read playlist-read-private'
    params = {
        'client_id': client_id,
        'response_type': 'code',
        'scope': scope,
        'redirect_uri': redirect_uri,
        'show_dialog': True
    }

    auth_url = f'https://accounts.spotify.com/authorize?{urllib.parse.urlencode(params)}'
    return redirect(auth_url)

@app.route('/get_playlists')
def get_playlists():
    token_info = session.get('token_info', None)
    
    if token_info and 'access_token' in token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        playlists = sp.current_user_playlists()
        playlist_names = [playlist['name'] for playlist in playlists['items']]
        return f'Your playlists: {", ".join(playlist_names)}'
    else:
        return 'Token not found. Please login first.'

if __name__ == '__main__':
    app.run()
