import time
from sb_user import SoundBubbleUser
from audio_manager import AudioManager
from flask import Flask, request, g, redirect, url_for, \
     abort, render_template, flash
from flask.ext.login import LoginManager, current_user, login_user, logout_user
from flask.ext.socketio import SocketIO, emit
from werkzeug import secure_filename

app = Flask(__name__)
app.config.from_object('config')
socket = SocketIO(app)

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
	data = audio.current_song
	data['server_time'] = time.time()
	emit('song change', data)

@socket.on('play')
def on_play():
	"""Sends a play command to MPD if the user is logged in."""
	if current_user.is_authenticated():
		audio.play()

@socket.on('pause')
def on_pause():
	"""Sends a pause command to MPD if the user is logged in."""
	if current_user.is_authenticated():
		audio.pause()

@socket.on('next song')
def on_next_song():
	"""Sends a next command to MPD if the user is logged in."""
	if current_user.is_authenticated():
		audio.play_next_song()

@socket.on('previous song')
def on_previous_song():
	"""Sends a previous command to MPD if the user is logged in."""
	if current_user.is_authenticated():
		audio.play_previous_song()




@app.route('/', methods=['GET', 'POST'])
def show_index():
	msg = None
	error = None

	if request.method == 'POST':
		if request.form['action'] == 'login':
			user = SoundBubbleUser.get(request.form['username'])
			if (user and user.password == request.form['password']):
				login_user(user, remember=True)
			else:
				error = 'Invalid username or password.'
		elif request.form['action'] == 'logout':
			logout_user()
		elif request.form['action'] == 'add_music' and current_user.is_authenticated():
			audio_file = request.files.get('song', None)
			if audio_file and audio.is_allowed_audio_file(audio_file.filename):
				filename = secure_filename(audio_file.filename)
				filepath = os.path.join(app.config['MUSIC_DIR'], filename)
				audio_file.save(filepath)

				data = audio.add_new_song(filename)

				msg = 'Added {} to the playlist.'.format(data['title'])

	return render_template('index.html', error=error, message=msg)



if __name__ == '__main__':
	socket.run(app, host='0.0.0.0')
