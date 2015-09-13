import time
import os.path
import hashlib
from mutagen import File
from select import select
from mpd import MPDClient
from threading import Thread
from flask import Flask, request, session, g, redirect, url_for, \
     abort, render_template, flash
from flask.ext.socketio import SocketIO, emit
from werkzeug import secure_filename

app = Flask(__name__)
app.config.from_object('config')
socket = SocketIO(app)

mpd = MPDClient()
mpd.connect(app.config['MPD_HOST'], app.config['MPD_PORT'])
mpd_locked = []

# Stores information on the currently playing song
current_song = None

def is_allowed_audio_file(filename):
	"""Returns True if the filename has an allowed audio extension."""
	return '.' in filename and filename.rsplit('.', 1)[1] in app.config['AUDIO_EXTENSIONS']

def get_album_artwork_url(current):
	"""Returns the URL for the currently playing song's artwork.
	If the artwork does not already exist on disk, it will be
	extracted from the audio file and saved.

	Args:
		current (dict): The return value from mpd.currentsong()

	Returns:
		A string containing the URL for the artwork.
	"""

	song_file = current.get('file', None)

	if song_file is None:
		return app.config['DEFAULT_ARTWORK']

	file_hash = hashlib.md5(song_file).hexdigest()
	image_file = app.config['COVERS_DIR'] + file_hash + '.' + app.config['COVERS_FILETYPE']

	if not os.path.isfile(image_file):
		song_file = File(app.config['MUSIC_DIR'] + song_file)

		if hasattr(song_file, 'pictures'):
			artwork = song_file.pictures
		elif 'covr' in song_file:
			artwork = song_file['covr'][0]
		elif 'APIC:' in song_file.tags:
			artwork = song_file.tags['APIC:'].data
		else:
			return app.config['DEFAULT_ARTWORK']

		with open(image_file, 'wb') as image:
			image.write(artwork)

	return image_file

def seconds_to_string(seconds):
	"""Converts seconds into a time string.
	Args:
		seconds (int): The total number of seconds.
	Returns:
		A time string as hh:mm:ss, or mm:ss if there are no hours.
	"""

	m, s = divmod(int(float(seconds)), 60)
	h, m = divmod(m, 60)

	if h:
		return '{:d}:{:02d}:{:02d}'.format(h, m, s)
	return '{:d}:{:02d}'.format(m, s)

def get_current_song():
	"""Updates the `current_song` global to contain updated information
	about the currently playing song. All connected clients are notified
	about the update.
	"""
	global current_song

	current = mpd.currentsong()
	status  = mpd.status()
	timestamp = time.time()

	current_song = {
		'artwork':    get_album_artwork_url(current),
		'title':      current['title'].decode('utf-8'),
		'artist':     current.get('artist', 'Unknown Artist').decode('utf-8'),
		'album':      current['album'].decode('utf-8'),
		'length_sec': current['time'],
		'time_sec':   status['elapsed'],
		'start_time': timestamp - int(float(status['elapsed'])),
		'length':     seconds_to_string(current['time']),
		'time':       seconds_to_string(status['elapsed']),
		'progress':   float(status['elapsed']) / float(current['time']) * 100,
		'is_playing': True if status['state'] == 'play' else False
	}

	data = current_song
	data['server_time'] = time.time()
	socket.emit('song change', data)

@socket.on('connect')
def on_connect():
	data = current_song
	data['server_time'] = time.time()
	emit('song change', data)

@socket.on('play')
def on_play():
	"""Sends a play command to MPD if the user is logged in."""
	if session['logged_in']:
		mpd_acquire()

		mpd.play()
		get_current_song()

		mpd_release()

@socket.on('pause')
def on_pause():
	"""Sends a pause command to MPD if the user is logged in."""
	if session['logged_in']:
		mpd_acquire()

		mpd.pause()
		get_current_song()

		mpd_release()

@socket.on('next song')
def on_next_song():
	"""Sends a next command to MPD if the user is logged in."""
	if session['logged_in']:
		mpd_acquire()

		mpd.next()
		get_current_song()

		mpd_release()

@socket.on('previous song')
def on_next_song():
	"""Sends a previous command to MPD if the user is logged in."""
	if session['logged_in']:
		mpd_acquire()

		mpd.previous()
		get_current_song()

		mpd.send_idle()

@app.route('/', methods=['GET', 'POST'])
def show_index():
	msg = None
	error = None

	global current_song

	if request.method == 'POST':
		if request.form['action'] == 'login':
			if request.form['username'] != app.config['USERNAME'] or request.form['password'] != app.config['PASSWORD']:
				error = 'Invalid username or password.'
			else:
				session['logged_in'] = True
		elif request.form['action'] == 'logout':
			session.pop('logged_in', None)
		elif request.form['action'] == 'add_music' and session['logged_in']:
			audio_file = request.files.get('song', None)
			if audio_file and is_allowed_audio_file(audio_file.filename):
				filename = secure_filename(audio_file.filename)
				filepath = os.path.join(app.config['MUSIC_DIR'], filename)
				audio_file.save(filepath)

				# Update the database and add it to the current playlist
				mpd_acquire()

				mpd.update()
				mpd.idle('database') # Wait for the database to be updated
				mpd.add(filename)

				song_title = mpd.find('filename', filename)[0]['title']

				mpd_release()

				msg = 'Added {} to the playlist.'.format(song_title)

	data = current_song
	data['server_time'] = time.time()
	return render_template('index.html', error=error, message=msg)

def mpd_acquire():
	"""Allows MPD commands to be executed by the main thread.
	mpd_release() must be called afterwards to allow the idle
	thread to continue polling."""
	mpd_locked.append(1)
	mpd.noidle()

def mpd_release():
	"""Allows the idle thread to continue waiting for subsystem changes."""
	mpd_locked.pop()
	mpd.send_idle()

def mpd_idle():
	"""Calls `mpd idle`, which waits for a change in an MPD subsystem.
	When a change is detected, connected clients are notified and
	`mpd idle` is called again.
	"""
	get_current_song()
	mpd.send_idle()

	while True:
		can_read = select([mpd], [], [], 0)[0]
		if can_read and not mpd_locked:
			changes = mpd.fetch_idle()

			if 'player' in changes:
				get_current_song()

			mpd.send_idle()

		time.sleep(1)

if __name__ == '__main__':
	# Spin off a thread to wait for changes in MPD subsystems
	mpd_thread = Thread(target=mpd_idle, name='mpd-worker', args=())
	mpd_thread.setDaemon(True)
	mpd_thread.start()

	socket.run(app, host='0.0.0.0')
