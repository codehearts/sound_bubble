(function() {

	var host     = 'http://' + window.location.host,
		socket   = io.connect(host),
		artwork  = document.querySelector('#current .artwork img'),
		title    = document.querySelector('#current .title'),
		artist   = document.querySelector('#current .artist'),
		album    = document.querySelector('#current .album'),
		time     = document.querySelector('#current .time'),
		length   = document.querySelector('#current .length'),
		progress = document.querySelector('#current progress'),
		button        = document.querySelector('#current .state-button'),
		next_button   = document.querySelector('#current .next-button'),
		file_forms    = document.querySelectorAll('.file-upload'),
		is_playing     = null,
		start_time     = 0,
		time_seconds   = 0,
		length_seconds = 0,

	/**
	 * Returns the current UNIX timestamp, in seconds.
	 */
	get_timestamp = function() {
		return Math.floor(Date.now() / 1000);
	},

	/**
	 * Converts a hh:mm:ss or mm:ss string into seconds.
	 * @param time_string (str) The time string to convert to seconds.
	 * @return (int) The number of seconds represented by the time string.
	 */
	string_to_seconds = function(time_string) {
		var time_split = time_string.split(':');

		// Hours were not provided
		if (time_split.length === 2) {
			return (+time_split[0]) * 60 + (+time_split[1]); 
		}

		return (+time_split[0]) * 3600 + (+time_split[1]) * 60 + (+time_split[2]); 
	},

	/**
	 * Converts seconds into a hh:mm:ss or mm:ss string.
	 * @param total_seconds (int) The number of seconds to convert to a string.
	 * @return (str) A time string representing that many seconds.
	 */
	seconds_to_string = function(total_seconds) {
		total_seconds = Math.floor(total_seconds);

		var h = Math.floor(total_seconds / 3600),
			m = Math.floor(total_seconds / 60),
			s = Math.floor(total_seconds % 60),
			str = '';

		// If it's over an hour long, show leading zeros on the minutes
		if (h) {
			str = h + ':' + (m < 10 ? '0' : '');
		}

		return str + m + ':' + (s < 10 ? '0' : '') + s;
	},

	/**
	 * Toggles the state of the play/pause button.
	 * Also updates the `is_playing` variable.
	 */
	toggle_button = function() {
		if (button) {
			if (is_playing) {
				button.classList.remove('play-button');
				button.classList.add('pause-button');
			} else {
				button.classList.add('play-button');
				button.classList.remove('pause-button');
			}
		}
	},

	/**
	 * Tells the server to play audio.
	 */
	play_audio = function() {
		socket.emit('play');
	},

	/**
	 * Tells the server to pause audio.
	 */
	pause_audio = function() {
		socket.emit('pause');
	},

	/**
	 * Tells the server to skip the current song.
	 */
	skip_audio = function() {
		socket.emit('next song');
	},

	/**
	 * Updates the information for the currently playing song.
	 * @param song_data (obj) Updated song data from the server.
	 */
	update_current_song = function(song_data) {
		// TODO Work on a doc frag of #current and then reflow once
		title.textContent  = song_data.title;
		artist.textContent = song_data.artist;
		album.textContent  = song_data.album;
		time.textContent   = song_data.time;
		length.textContent = song_data.length;
		progress.value     = song_data.progress;
		artwork.src        = song_data.artwork;

		if (is_playing === null) {
			is_playing = song_data.is_playing;
			toggle_button();
		}

		if (is_playing !== song_data.is_playing) {
			is_playing = !is_playing;
			toggle_button();
		}

		var time_diff = get_timestamp() - song_data.server_time;
		start_time = song_data.start_time + time_diff;
		progress.setAttribute('data-start-time', start_time);

		time_seconds   = parseFloat(song_data.time_sec);
		length_seconds = parseInt(song_data.length_sec, 10);
	},
	
	/**
	 * Increments the playback time for the current song.
	 */
	increment_time = function() {
		// Do nothing if playback is paused or the song is over
		if (!is_playing || time_seconds >= length_seconds) {
			return;
		}

		time_seconds = get_timestamp() - start_time;

		// Update the current time
		time.textContent = seconds_to_string(time_seconds);
		progress.value = time_seconds / length_seconds * 100;
	},

	/**
	 * Initializes the sound_bubble instance.
	 */
	init = function() {
		if (button) {
			// Handle play/pause button
			button.addEventListener('click', function() {
				if (button.classList.contains('play-button')) {
					play_audio();
				} else {
					pause_audio();
				}

				toggle_button();
			});
		}

		if (next_button) {
			// Handle skip button
			next_button.addEventListener('click', skip_audio);
		}

		if (file_forms) {
			var file_fields = document.querySelectorAll('.file-upload input[type=file]');
			for (var i = 0; i < file_fields.length; i++) {
				file_fields[i].addEventListener('change', function() {
					this.parentNode.classList.add('active');
					this.parentNode.submit();
				});
			}
		}

		// Tells the server that we've connected
		socket.on('connect', function() {
			socket.emit('connect');

			increment_time();
			window.setInterval(increment_time, 1000);
		});

		// Updates the current song when the server sends a 'song change' event
		socket.on('song change', update_current_song);
	};

	init();

	return {};

}());
