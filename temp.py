from dotenv import load_dotenv
import os
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from flask import Flask, redirect, url_for, session, request, render_template, send_file
import urllib.parse
from PIL import Image, ImageDraw
from io import BytesIO
import requests
import base64
from flask import Flask, render_template
from colorthief import ColorThief


app = Flask(__name__)


@app.route('/')
def hello():
    return redirect(url_for('generate_image', do_generate="False"))


@app.route('/generate_image')
def generate_image():
    do_desktop = request.args.get('do_generate', type=str)
    
    print(do_desktop, type(do_desktop))
    
    if do_desktop == "True":
        background = Image.new('RGB', (1920, 1080), 'black')
    else:
        background = Image.new('RGB', (1179,2556), 'black')

    image_url = 'https://www.wpbeginner.com/wp-content/uploads/2020/03/ultimate-small-business-resource-coronavirus.png'
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
    app.run(debug=True)