import time
from sb_user import SoundBubbleUser
from audio_manager import AudioManager
from flask import Flask, request, redirect, url_for, \
     render_template, session
from flask.ext.login import LoginManager, current_user, login_user, logout_user
from flask.ext.socketio import SocketIO, emit
from werkzeug import secure_filename
import os.path

app = Flask(__name__)
app.config.from_object('config')
socket = SocketIO(app, async_mode='threading')

SoundBubbleUser.register_users({
	app.config['USERNAME']: app.config['PASSWORD']
})

login_manager = LoginManager()
login_manager.init_app(app)

audio = AudioManager(app.config)



@login_manager.user_loader
def load_user(id):
    return SoundBubbleUser.get(id)



@audio.on('song change')
def notify_song_change(song):
	song['server_time'] = time.time()
	socket.emit('song change', song)



@socket.on('connect')
def on_connect():
	pass

@socket.on('get current song')
def on_get_current_song():
	data = audio.current_song
	data['server_time'] = time.time()
	emit('song change', data)

@socket.on('play')
def on_play():
	"""Sends a play command to MPD if the user is logged in."""
	if current_user.is_authenticated:
		audio.play()

@socket.on('pause')
def on_pause():
	"""Sends a pause command to MPD if the user is logged in."""
	if current_user.is_authenticated:
		audio.pause()

@socket.on('next song')
def on_next_song():
	"""Sends a next command to MPD if the user is logged in."""
	if current_user.is_authenticated:
		audio.play_next_song()

@socket.on('previous song')
def on_previous_song():
	"""Sends a previous command to MPD if the user is logged in."""
	if current_user.is_authenticated:
		audio.play_previous_song()



def redirect_url(default='index'):
    return request.args.get('next') or \
           request.referrer or \
           url_for(default)

@app.route('/', methods=['GET'])
def show_index():
	msg = session.pop('message', None)
	error = session.pop('error', None)

	return render_template('index.html', error=error, message=msg, music_script=True)

@app.route('/login/', methods=['POST'])
def login():
	if request.method == 'POST':
		user = SoundBubbleUser.get(request.form['username'])
		if (user and user.password == request.form['password']):
			login_user(user, remember=True)
		else:
			session['error'] = 'Invalid username or password.'

	return redirect(redirect_url())

@app.route('/logout/', methods=['POST'])
def logout():
	if request.method == 'POST':
		logout_user()

	return redirect(redirect_url())

@app.route('/upload/music/', methods=['POST'])
def upload_music():
	if request.method == 'POST' and current_user.is_authenticated:
		audio_file = request.files.get('song', None)
		if audio_file and audio.is_allowed_audio_file(audio_file.filename):
			filename = secure_filename(audio_file.filename)
			filepath = os.path.join(app.config['MUSIC_DIR'], filename)
			audio_file.save(filepath)

			audio.update_database()
			data = audio.add_new_song(filename)

			session['message'] = 'Added {} to the playlist.'.format(data['title'])

	return redirect(redirect_url())

@app.route('/upload/artwork/', methods=['POST'])
def upload_artwork():
	if request.method == 'POST' and current_user.is_authenticated:
		artwork_file = request.files.get('artwork', None)
		if artwork_file and audio.is_allowed_artwork_file(artwork_file.filename):
			filename = secure_filename(artwork_file.filename)
			filepath = os.path.join(app.config['TMP_DIR'], filename)
			artwork_file.save(filepath)

			song_title = audio.current_song['title']
			audio.change_album_artwork(audio.current_song, filepath)

			session['message'] = 'Updated artwork for {}.'.format(song_title)

	return redirect(redirect_url())

@app.route('/add/', methods=['POST'])
def add_music():
	song_count = 0

	if request.method == 'POST' and current_user.is_authenticated:
		audio_files = request.form.getlist('files')

		for audio_file in audio_files:
			if audio.is_allowed_audio_file(audio_file):
				audio.add_new_song(audio_file)
				song_count += 1

	session['message'] = 'Added {} songs to the playlist.'.format(song_count)
	return redirect(redirect_url())

@app.route('/albums/', methods=['GET', 'POST'])
def show_albums():
	msg = session.pop('message', None)
	error = session.pop('error', None)

	return render_template('albums.html', error=error, message=msg, albums=[])

@app.route('/albums/<album_filter>', methods=['GET', 'POST'])
def albums_by(album_filter):
	msg = session.pop('message', None)
	error = session.pop('error', None)

	if album_filter == '1-9':
		album_filter = '1'
	elif album_filter == 'other':
		album_filter = '#'

	albums = audio.get_albums(album_filter)

	return render_template('albums.html', error=error, message=msg, albums=albums)



if __name__ == '__main__':
	socket.run(app, host='0.0.0.0')
