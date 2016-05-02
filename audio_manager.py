from musicgen import MusicGen
from threading import Thread
from os import path, remove
from shutil import copyfile
from select import select
from mpd import MPDClient
from hashlib import md5
from PIL import Image
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
						   MPD_HOST:           The hostname of the MPD instance.
						   MPD_PORT:           The port that the MPD instance is running on.
						   PLAYLIST:           The name of the MPD playlist to use.
						   MUSIC_DIR:          The directory that MPD looks for music in.
						   DEFAULT_ARTWORK:    The URL for default album artwork.
						   COVERS_DIR:         The directory to save album covers to.
						   COVERS_FILETYPE:    The file format to save album covers in.
						   AUDIO_EXTENSIONS:   List of allowed audio file extensions.
						   ARTWORK_EXTENSIONS: List of allowed artwork file extensions.
		"""
		self._locks = []
		self._callbacks = {}
		self._idling = False
		self._config = config
		self._mpd = MPDClient(use_unicode=True)
		self._musicgen = MusicGen()
		self.playlist = config['PLAYLIST']

		self._mpd.connect(config['MPD_HOST'], config['MPD_PORT'])

		self.current_song = None

		# Load the Sound Bubble playlist
		self._ensure_playlist_exists(self.playlist)
		self.load_playlist()

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
		if (self._idling):
			self._mpd.noidle()
			self._idling = False

	def _mpd_release(self):
		"""Allows the idle thread to continue waiting for subsystem changes."""
		self._locks.pop()
		if (not self._locks and not self._idling):
			self._mpd.send_idle()
			self._idling = True

	def _mpd_idle(self):
		"""
		Calls `mpd idle`, which waits for a change in an MPD subsystem.
		When a change is detected, connected clients are notified and
		`mpd idle` is called again.
		"""
		self._update_current_song()
		self._mpd.send_idle()
		self._idling = True

		while True:
			can_read = select([self._mpd], [], [], 0)[0]
			if can_read and not self._locks:
				self._idling = False
				changes = self._mpd.fetch_idle()

				if 'player' in changes:
					self._update_current_song()

				self._mpd.send_idle()
				self._idling = True

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



	def _ensure_playlist_exists(self, name):
		"""
		Ensures that the given playlist exists, and creates it if now.
		If the playlist must be created, the current song queue will be cleared.

		Arguments:
			name (str): The name of the playlist that should exist.
		"""
		for playlist in self._mpd.listplaylists():
			if playlist['playlist'] == name:
				return

		self._mpd.clear()    # Empty the current song queue
		self._mpd.save(name) # Save the empty playlist

	def load_playlist(self):
		"""
		Sets the current MPD playlist to the Sound Bubble playlist.
		"""
		self._mpd.clear()             # Empty the current song queue
		self._mpd.load(self.playlist) # Load songs from the Sound Bubble playlist



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


	def update_database(self):
		"""
		Updates the MPD database. This should be called after new music has been added,
		such as after a file upload.
		"""
		self._mpd_acquire()
		self._mpd.update()
		self._mpd.idle('database') # Wait for the database to be updated
		self._mpd_release()

	def add_new_song(self, filename):
		"""
		Add a file to the Sound Bubble playlist.

		Arguments:
			filename (str): The name of the file relative to the music directory.

		Returns:
			A dict of song data for the added song.
		"""
		self._mpd_acquire()

		self._mpd.add(filename)
		self._mpd.playlistadd(self.playlist, filename)

		song = self._mpd.find('filename', filename)[0]

		self._mpd_release()

		return song

	def is_allowed_audio_file(self, filename):
		"""Returns True if the filename has an allowed audio extension."""
		return '.' in filename and filename.rsplit('.', 1)[1] in self._config['AUDIO_EXTENSIONS']

	def is_allowed_artwork_file(self, filename):
		"""Returns True if the filename has an allowed artwork extension."""
		return '.' in filename and filename.rsplit('.', 1)[1] in self._config['ARTWORK_EXTENSIONS']



	def _get_album_artwork_url(self, song_file):
		"""Returns the URL for the currently playing song's artwork.

		If the artwork does not already exist on disk, it will be
		extracted from the audio file. A resized version of the
		artwork will be created and used to reduce bandwidth.

		Arguments:
			song_file (str): The filename of the audio file.

		Returns:
			A string containing the URL for the resized artwork.
		"""
		song_path        = path.join(self._config['MUSIC_DIR'], song_file)

		# The image filename is a hash of the song's filename
		file_hash        = md5(song_file).hexdigest()
		file_hash_path   = path.join(self._config['COVERS_DIR'], file_hash)
		image_file       = file_hash_path + self._config['COVERS_FILETYPE']

		# The resized image filename is {image_filename}_{width}_{height}
		resized_filename = file_hash_path + '_' + '_'.join(map(str, self._config['COVERS_SIZE']))
		resized_file     = resized_filename + self._config['COVERS_FILETYPE']

		if not path.isfile(image_file):
			try:
				self._musicgen.extract_cover_art(song_path, out_file=image_file)
			except (IOError, NoAlbumArtError):
				# Return the default no-album-cover image
				return '/' + path.join(self._config['COVERS_DIR'], self._config['DEFAULT_ARTWORK'])

			resize = Image.open(image_file)
			resize.thumbnail(self._config['COVERS_SIZE'])
			resize.save(resized_file)

		return '/' + resized_file

	def get_albums(self, filter_by):
		"""
		Returns a filtered list of albums, including their songs and artwork.
		
		Arguments:
			filter_by (str): Either a letter of the alphabet, a number, or #.
							 Alpha: Only albums begining with that letter are returned.
							 Numeric: Only albums begining with a number are returned.
							 #: Albums begining with any other character are returned.
							 Another other value will default to '#'.

		Returns:
			A list of albums dicts with the following fields:
			name:  The name of the album.
			cover: URL of the album artwork, taken from the first song.
			songs: List of song dicts, as returned by MPDClient.find().
			       The song dict is modified to contain an 'in_playlist' key,
				   which is True if the song is in the current playlist and False otherwise.
		"""
		# Values for the type of filter we're using
		alpha   = 0
		numeric = 1
		other   = 2

		filter_type = alpha           # The type of filter to apply to the albums
		filter_by = filter_by.lower() # The actual filter value to apply
		if not filter_by.isalnum():
			filter_type = other
			filter_by = '#'
		elif filter_by.isdigit():
			filter_type = numeric
			filter_by = '1'

		albums = []

		self._mpd_acquire()
		current_playlist = self._mpd.playlist() # Get all songs in current playlist
		album_names = self._mpd.list('album')   # Get all album names

		for album in album_names:
			# Skip albums which do not meet the filter
			if filter_type == alpha and album[0].lower() != filter_by:
				continue
			elif filter_type == numeric and not album[0].isdigit():
				continue
			elif filter_type == other and album[0].isalnum():
				continue

			# Find songs in the album
			songs = self._mpd.find('Album', album)

			# Retrieve the album art from the first song
			art = self._get_album_artwork_url(songs[0]['file'])

			# Set in_playlist to True if the song is in the current playlist, False otherwise
			for song in songs:
				if 'file: ' + song['file'] in current_playlist:
					song['in_playlist'] = True
				else:
					song['in_playlist'] = False

			albums.append({
				'name':  album,
				'songs': songs,
				'cover': art
			})
		self._mpd_release()

		return albums

	def change_album_artwork(self, song_file, artwork_file):
		"""Embeds the given artwork in the given song file.
		The artwork file will then be deleted once embedded.

		Arguments:
			song_file (str): The filename of the song to modify the cover art of.
			artwork_file (str): The path to the artwork file to embed.
		"""
		song_path = path.join(self._config['MUSIC_DIR'], song_file)

		# The image filename is a hash of the song's filename
		file_hash      = md5(song_file).hexdigest()
		file_hash_path = path.join(self._config['COVERS_DIR'], file_hash)
		image_file     = file_hash_path + self._config['COVERS_FILETYPE']

		self._musicgen.embed_cover_art(song_path, image_file)

		# Remove existing cached artwork
		if path.isfile(image_file):
			# The resized image filename is {image_filename}_{width}_{height}
			resized_filename = file_hash_path + '_' + '_'.join(map(str, self._config['COVERS_SIZE']))
			resized_file     = resized_filename + self._config['COVERS_FILETYPE']

			remove(resized_file)
			remove(image_file)

		remove(artwork_file)

		# Update the data for the current song
		self._mpd_acquire()
		self._update_current_song(reset_cache=True)
		self._mpd_release()

	def _update_current_song(self, reset_cache=False):
		"""
		Updates the `current_song` global to contain updated information
		about the currently playing song.
		"""
		cache_control = ''
		if reset_cache:
			cache_control = '?=' + str(time.time())

		timestamp = time.time()
		current = self._mpd.currentsong()

		if current == {}:
			self.current_song = {
				'artwork':    self._get_album_artwork_url('') + cache_control,
				'file':       '',
				'title':      'Empty Playlist',
				'artist':     '',
				'album':      '',
				'length_sec': '',
				'time_sec':   '',
				'start_time': timestamp,
				'length':     '',
				'time':       '',
				'progress':   0,
				'is_playing': False
			}

			self.fire_event('song change', self.current_song)
			return

		status = self._mpd.status()

		self.current_song = {
			'artwork':    self._get_album_artwork_url(current['file']) + cache_control,
			'file':       current['file'],
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
