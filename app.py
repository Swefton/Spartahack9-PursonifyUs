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

def calculate_average(features_list):
    return sum(features_list) / len(features_list) if len(features_list) > 0 else 0

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
    token_info = session.get('token_info', None)
    if token_info and 'access_token' in token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        playlist_id = request.args.get('playlist_id')

        # Get the tracks in the playlist
        results = sp.playlist_items(playlist_id, fields='items.track(name, id, artists.name, album.name)', limit=50)

        # Create a list to store the details of each track
        track_details = []

        # Create lists to store audio feature values for averaging
        acousticness_list = []
        danceability_list = []
        energy_list = []
        instrumentalness_list = []
        liveness_list = []
        loudness_list = []
        speechiness_list = []
        tempo_list = []

        # Populate the track_details list and audio feature lists
        for track in results['items']:
            track_id = track['track']['id']
            track_details.append(track['track']['name'])

            # Get audio features for each track
            audio_features = sp.audio_features([track_id])[0]

            # Append feature values to respective lists
            acousticness_list.append(audio_features['acousticness'])
            danceability_list.append(audio_features['danceability'])
            energy_list.append(audio_features['energy'])
            instrumentalness_list.append(audio_features['instrumentalness'])
            liveness_list.append(audio_features['liveness'])
            loudness_list.append(audio_features['loudness'])
            speechiness_list.append(audio_features['speechiness'])
            tempo_list.append(audio_features['tempo'])

        # Calculate the average of each audio feature
        avg_acousticness = calculate_average(acousticness_list)
        avg_danceability = calculate_average(danceability_list)
        avg_energy = calculate_average(energy_list)
        avg_instrumentalness = calculate_average(instrumentalness_list)
        avg_liveness = calculate_average(liveness_list)
        avg_loudness = calculate_average(loudness_list)
        avg_speechiness = calculate_average(speechiness_list)
        avg_tempo = calculate_average(tempo_list)

        return f'Analysis for playlist with ID: {playlist_id} <br>' \
               f'50 Most Recent Songs:<br>{"<br>".join(track_details)}<br><br>' \
               f'Average Audio Features:<br>' \
               f'Acousticness: {avg_acousticness}<br>' \
               f'Danceability: {avg_danceability}<br>' \
               f'Energy: {avg_energy}<br>' \
               f'Instrumentalness: {avg_instrumentalness}<br>' \
               f'Liveness: {avg_liveness}<br>' \
               f'Loudness: {avg_loudness}<br>' \
               f'Speechiness: {avg_speechiness}<br>' \
               f'Tempo: {avg_tempo}'

    else:
        return redirect('/login')

if __name__ == '__main__':
    app.run()
