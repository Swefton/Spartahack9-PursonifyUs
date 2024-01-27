from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, redirect, url_for, session, request, jsonify
import urllib.parse

load_dotenv()

client_id = os.getenv("SPOTIFY_CLIENT_ID")
client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
redirect_uri = os.getenv("SPOTIFY_REDIRECT_URI")

app = Flask(__name__)
app.secret_key = os.urandom(24)

@app.route('/')
def index():
    logout_link = ''
    if 'user_id' in session:
        logout_link = '<a href="/logout">Logout</a>'
    return 'Hello, World! <a href="/login">Login</a> {}'.format(logout_link)

@app.route('/callback')
def callback():
    code = request.args.get('code')
    state = request.args.get('state')
    print(code, state)
    if code:
        sp_oauth = SpotifyOAuth(client_id, client_secret, redirect_uri, scope='user-library-read playlist-read-private', cache_path=".cache")
        token_info = sp_oauth.get_access_token(code)

        sp = spotipy.Spotify(auth_manager=sp_oauth)
        user_info = sp.current_user()
        user_id = user_info['id']

        session['user_id'] = user_id
        session['token_info'] = token_info

        return f'Logged in as {user_info}. <a href="/get_playlists">Get Playlists</a>'
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

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/get_playlists')
def get_playlists():
    token_info = session.get('token_info', None)
    
    if token_info and 'access_token' in token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        playlists = sp.current_user_playlists()

        if playlists and 'items' in playlists:
            playlist_info_list = []

            for playlist in playlists['items']:
                try:
                    playlist_id = playlist['id']
                    playlist_name = playlist['name']

                    tracks = sp.playlist_tracks(playlist_id, limit=10)

                    total_tracks = tracks['total']
                    total_duration_ms = sum([track['track']['duration_ms'] for track in tracks['items']])
                    total_duration_min = total_duration_ms / 60000

                    playlist_info = {
                        'playlist_name': playlist_name,
                        'playlist_id': playlist_id,
                        'total_tracks': total_tracks,
                        'total_duration_min': total_duration_min,
                        'trackids': [track['track']['id'] for track in tracks['items']]
                    }

                    playlist_info_list.append(playlist_info)
                except:
                    pass
            print(playlist_info_list)
            playlist_links = []
            for playlist_info in playlist_info_list:
                playlist_id = playlist_info['playlist_id']
                playlist_links.append(f'<a href="/analysis?playlist_id={playlist_id}">{playlist_info["playlist_name"]}</a>')
            return '<br>'.join(playlist_links)    
        
        else:
            return 'No playlists found for the user.'

    else:
        return 'Token not found. Please login first.'
    
@app.route('/analysis')
def analysis():
    playlist_id = request.args.get('playlist_id')

    return f'Analysis for playlist with ID: {playlist_id}'

if __name__ == '__main__':
    app.run()
