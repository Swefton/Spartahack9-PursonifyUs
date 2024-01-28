from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, redirect, url_for, session, request, render_template, send_file
import urllib.parse
from PIL import Image
from io import BytesIO
import requests
from colorthief import ColorThief
from openai import OpenAI
import time



load_dotenv()

# Access the environment variables
client_id = os.getenv('SPOTIFY_CLIENT_ID')
client_secret = os.getenv('SPOTIFY_CLIENT_SECRET')
redirect_uri = os.getenv('SPOTIFY_REDIRECT_URI')
openai_key = os.getenv('OPENAI_KEY')


def calculate_average(features_list):
    return sum(features_list) / len(features_list) if len(features_list) > 0 else 0

app = Flask(__name__)
app.secret_key = os.urandom(24)
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True

sp_oauth = SpotifyOAuth(client_id, client_secret, redirect_uri, scope='user-library-read playlist-read-private', cache_path=None)


@app.route('/')
def index():
    logout_link = ''
    if 'user_id' in session:
        logout_link = '<a href="/logout">Logout</a>'
    return render_template('landing.html', logout_link=logout_link)

@app.route('/callback')
def callback():
    time.sleep(3)
    code = request.args.get('code')
    print(code)
    if code:
        token_info = sp_oauth.get_access_token(code)
        sp = spotipy.Spotify(auth_manager=sp_oauth)
        user_info = sp.current_user()
        user_id = user_info['id']

        session['user_id'] = user_id
        session['token_info'] = token_info

        return render_template('confirmation.html', user_info=user_info)
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
    time.sleep(3)
    if token_info and 'access_token' in token_info:
        sp = spotipy.Spotify(auth=token_info['access_token'])
        playlists = sp.current_user_playlists()

        if playlists and 'items' in playlists:
            playlist_info_list = []

            for playlist in playlists['items'][:3]:
                try:
                    playlist_id = playlist['id']
                    playlist_name = playlist['name']

                    tracks = sp.playlist_tracks(playlist_id, limit=10)

                    total_tracks = tracks['total']
                    total_duration_ms = sum([track['track']['duration_ms'] for track in tracks['items']])
                    total_duration_min = int(round(total_duration_ms / 60000))

                    playlist_info = {
                        'playlist_name': playlist_name,
                        'playlist_id': playlist_id,
                        'total_tracks': total_tracks,
                        'total_duration_min': total_duration_min,
                        'image_url': playlist['images'][0]['url'] if len(playlist['images']) > 0 else ''
                    }

                    playlist_info_list.append(playlist_info)
                except:
                    pass
            playlist_links = []
            for playlist_info in playlist_info_list:
                playlist_id = playlist_info['playlist_id']
                playlist_links.append(f'<a href="/analysis?playlist_id={playlist_id}">{playlist_info["playlist_name"]}</a>')
            return render_template('playlists.html', playlist_info_list=playlist_info_list)
        
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

        playlist_info = sp.playlist(playlist_id, fields='name,description')
        playlist_name = playlist_info['name']
        playlist_description = playlist_info['description']
        results = sp.playlist_items(playlist_id, fields='items.track(name, id, artists.name, album.name)', limit=25)

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
            time.sleep(0.5)
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

        return render_template('analysis.html',
                               playlist_id=playlist_id,
                               playlist_name=playlist_name,
                               playlist_description=playlist_description,
                               track_details=track_details,
                               avg_acousticness=avg_acousticness,
                               avg_danceability=avg_danceability,
                               avg_energy=avg_energy,
                               avg_instrumentalness=avg_instrumentalness,
                               avg_liveness=avg_liveness,
                               avg_loudness=avg_loudness,
                               avg_speechiness=avg_speechiness,
                               avg_tempo=avg_tempo)

    else:
        return redirect('/login')

@app.route('/generate_image')
def generate_image():
    do_desktop = request.args.get('do_generate', type=str)
    name = request.args.get('name', type=str)
    disc = request.args.get('disc', type=str)
    tracks = request.args.getlist('tracks')
    client = OpenAI(api_key=openai_key)



    response = client.images.generate(
    model="dall-e-2",
    prompt=f"aesthetic wallpaper titeld {name} about {disc} with {', '.join(tracks[0:3])}", 
    size="512x512",
    quality="standard",
    n=1,
    )

    image_url = response.data[0].url
    
    
    if do_desktop == "True":
        background = Image.new('RGB', (1920, 1080), 'black')
    else:
        background = Image.new('RGB', (1179,2556), 'black')

    image_data = BytesIO(requests.get(image_url).content)
    center_image = Image.open(image_data)

    x_position = (background.width - center_image.width) // 2
    y_position = (background.height - center_image.height) // 2

    background.paste(center_image, (x_position, y_position))

    # Use colorthief to get the dominant color of the image
    color_thief = ColorThief(image_data)
    dominant_color = color_thief.get_color(quality=1)

    # Set the background color dynamically
    background = Image.new('RGB', background.size, dominant_color)
    background.paste(center_image, (x_position, y_position))

    output_buffer = BytesIO()
    background.save(output_buffer, format='PNG')
    output_buffer.seek(0)

    return send_file(output_buffer, mimetype='image/png')


if __name__ == '__main__':
    app.run()
