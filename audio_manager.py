from threading import Thread
from select import select
from mpd import MPDClient
from mutagen import File
from hashlib import md5
import os.path
import time

class AudioManager(object):
	"""
	Provides an interface to a running MPD instance.

	This class also accepts callbacks to be run after the following events are fired:
		'song change': Currently playing song has changed.
		               Callback should accept current song dict as its only argument.

	Callbacks can be registered as per the following example:

		music = SongData(config)

		@music.on('song change')
		def handle_song_change(song):
			print('Song is now {}.'.format(song['title']))

	Properties:
		current_song (dict): Information on the currently playing song.
		                     This dict includes the following keys:
							 artwork:    The URL for the song's artwork.
							 title:      The title of the current song.
							 artist:     The artist of the current song.
							 album:      The album of the current song.
							 length_sec: The length of the song in seconds.
							 time_sec:   The amount of time into the song, in seconds.
							 start_time: UNIX timestamp for when the song began playing.
							 length:     The length of the song as a time string.
							 time:       The amount of time into the song, as a time string.
							 progress:   The percentage of the amount of time into the song.
							 is_playing: True if the song is playing, False otherwise.
	"""

	def __init__(self, config):
		"""
		Creates a new interface to a running MPD instance.

		Arguments:
			config (dict): A dictionary of config values.
			               This is expected to include the following keys:
						   MPD_HOST:        The hostname of the MPD instance
						   MPD_PORT:        The port that the MPD instance is running on
						   MUSIC_DIR:       The directory that MPD looks for music in.
						   DEFAULT_ARTWORK: The URL for default album artwork.
						   COVERS_DIR:      The directory to save album covers to.
						   COVERS_FILETYPE: The file format to save album covers in.
		"""
		self._locks = []
		self._callbacks = {}
		self._config = config
		self._mpd = MPDClient()
		self._mpd.connect(config['MPD_HOST'], config['MPD_PORT'])

		self.current_song = None

		# Spin off a thread to wait for changes in MPD subsystems
		self._mpd_thread = Thread(target=self._mpd_idle, name='mpd-worker', args=())
		self._mpd_thread.setDaemon(True)
		self._mpd_thread.start()



	def on(self, name):
		"""
		Decorator for adding a callback method for events.

		Example:
			music = SongData(config)

			@music.on('song change')
			def handle_song_change(song):
				print('Song is now {}.'.format(song['title']))

		Arguments:
			name (str): The name of the event to register the callback for.
		"""
		def func_wrapper(func):
			self._callbacks[name] = func
			return func
		return func_wrapper

	def fire_event(self, name, *args, **kwargs):
		"""
		Fires the given event, passing the given arguments to the callback.

		Arguments:
			name (str): The name of the event to fire.
		"""
		func = self._callbacks.get(name, None)
		if not func is None:
			return func(*args, **kwargs)



	def _mpd_acquire(self):
		"""
		Allows MPD commands to be executed by the main thread.
		mpd_release() must be called afterwards to allow the idle
		thread to continue polling.
		"""
		self._locks.append(1)
		self._mpd.noidle()

	def _mpd_release(self):
		"""Allows the idle thread to continue waiting for subsystem changes."""
		self._locks.pop()
		self._mpd.send_idle()

	def _mpd_idle(self):
		"""
		Calls `mpd idle`, which waits for a change in an MPD subsystem.
		When a change is detected, connected clients are notified and
		`mpd idle` is called again.
		"""
		self._update_current_song()
		self._mpd.send_idle()

		while True:
			can_read = select([self._mpd], [], [], 0)[0]
			if can_read and not self._locks:
				changes = self._mpd.fetch_idle()

				if 'player' in changes:
					self._update_current_song()

				self._mpd.send_idle()

			time.sleep(1)



	def seconds_to_string(self, seconds):
		"""
		Converts seconds into a time string.

		Arguments:
			seconds (int): The total number of seconds.

		Returns:
			A time string as hh:mm:ss, or mm:ss if there are no hours.
		"""
		m, s = divmod(int(float(seconds)), 60)
		h, m = divmod(m, 60)

		if h:
			return '{:d}:{:02d}:{:02d}'.format(h, m, s)
		return '{:d}:{:02d}'.format(m, s)



	def play(self):
		"""Plays the current song"""
		self._mpd_acquire()

		self._mpd.play()
		self._update_current_song()

		self._mpd_release()

	def pause(self):
		"""Pauses the current song"""
		self._mpd_acquire()

		self._mpd.pause()
		self._update_current_song()

		self._mpd_release()

	def play_previous_song(self):
		"""Plays the previous song."""
		self._mpd_acquire()

		self._mpd.previous()
		self._update_current_song()

		self._mpd_release()

	def play_next_song(self):
		"""Plays the next song."""
		self._mpd_acquire()

		self._mpd.next()
		self._update_current_song()

		self._mpd_release()


	def add_new_song(self, filename):
		"""
		Updates the database and add a new file to the current playlist.

		Arguments:
			filename (str): The name of the file relative to the music directory.

		Returns:
			A dict of song data for the added song.
		"""
		self._mpd_acquire()

		self._mpd.update()
		self._mpd.idle('database') # Wait for the database to be updated
		self._mpd.add(filename)

		song = self._mpd.find('filename', filename)[0]

		self._mpd_release()

		return song

	def is_allowed_audio_file(self, filename):
		"""Returns True if the filename has an allowed audio extension."""
		return '.' in filename and filename.rsplit('.', 1)[1] in self._config['AUDIO_EXTENSIONS']



	def _get_album_artwork_url(self, current):
		"""Returns the URL for the currently playing song's artwork.
		If the artwork does not already exist on disk, it will be
		extracted from the audio file and saved.

		Arguments:
			current (dict): The return value from mpd.currentsong()

		Returns:
			A string containing the URL for the artwork.
		"""
		song_file = current.get('file', None)

		if song_file is None:
			return self._config['DEFAULT_ARTWORK']

		file_hash = md5(song_file).hexdigest()
		image_file = self._config['COVERS_DIR'] + file_hash + '.' + self._config['COVERS_FILETYPE']

		if not os.path.isfile(image_file):
			song_file = File(self._config['MUSIC_DIR'] + song_file)

			if hasattr(song_file, 'pictures'):
				artwork = song_file.pictures
			elif 'covr' in song_file:
				artwork = song_file['covr'][0]
			elif 'APIC:' in song_file.tags:
				artwork = song_file.tags['APIC:'].data
			else:
				return self._config['DEFAULT_ARTWORK']

			with open(image_file, 'wb') as image:
				image.write(artwork)

		return image_file

	def _update_current_song(self):
		"""
		Updates the `current_song` global to contain updated information
		about the currently playing song.
		"""
		current = self._mpd.currentsong()
		status  = self._mpd.status()
		timestamp = time.time()

		self.current_song = {
			'artwork':    self._get_album_artwork_url(current),
			'title':      current['title'].decode('utf-8'),
			'artist':     current.get('artist', 'Unknown Artist').decode('utf-8'),
			'album':      current['album'].decode('utf-8'),
			'length_sec': current['time'],
			'time_sec':   status['elapsed'],
			'start_time': timestamp - int(float(status['elapsed'])),
			'length':     self.seconds_to_string(current['time']),
			'time':       self.seconds_to_string(status['elapsed']),
			'progress':   float(status['elapsed']) / float(current['time']) * 100,
			'is_playing': True if status['state'] == 'play' else False
		}

		self.fire_event('song change', self.current_song)
