from mutagen.id3 import ID3, APIC, error
from mutagen.flac import Picture, FLAC
from mutagen.mp4 import MP4, MP4Cover
from mutagen.mp3 import MP3
from mutagen import File
from os import path

class MusicGen(object):
	"""A wrapper for mutagen which unifies the API for differing filetypes."""

	def __init__(self):
		super(MusicGen, self).__init__()

	def extract_cover_art(self, audio_file, out_file=None):
		"""Extracts cover artwork from an audio file.

		If no output file is specified, the image data is return.
		Otherwise, the image data is written to the output file.

		Arguments:
			audio_file (str): The path to the audio file.

		Kwargs:
			out_file (str): The output file to write the artwork to.

		Exceptions:
			RuntimeWarning: Raised when the image file has no artwork.
			IOError: Raised when the given audio file is a directory,
			         or the file does not exist.

		Returns:
			Nothing if an output file is specified, otherwise
			the cover art image data is returned.
		"""
		audio_file = File(audio_file)
		artwork = None

		if hasattr(audio_file, 'pictures') and len(audio_file.pictures):
			# FLAC
			artwork = audio_file.pictures[0].data
		elif 'covr' in audio_file:
			# MP3
			artwork = audio_file['covr'][0]
		elif hasattr(audio_file, 'tags'):
			# M4A
			apic_keys = [k for k in audio_file.tags.keys() if k.startswith('APIC:')]
			if apic_keys:
				artwork = audio_file.tags[apic_keys[0]].data

		if artwork is None:
			raise RuntimeWarning('{} contains no artwork.'.format(audio_file))

		# Return the artwork data if no output file is specified
		if out_file is None:
			return artwork

		# Otherwise, write to the output file
		with open(out_file, 'wb') as image_file:
			image_file.write(artwork)
		
	def embed_cover_art(self, audio_file, cover_file):
		"""Embeds cover art into an audio file.

		Arguments:
			audio_file (str): The path to the audio file to embed the artwork in.
			cover_file (str): The path to the artwork file to embed.
		"""
		if path.isfile(audio_file) and path.isfile(cover_file):
			mimetype = 'image/png' if cover_file.endswith('png') else 'image/jpeg'
			artwork  = open(cover_file, 'rb').read()
			desc     = u'Cover Art'

			# Determine which filetype we're handling
			if audio_file.endswith('m4a'):
				audio = MP4(audio_file)

				covr = []
				if cover_file.endswith('png'):
					covr.append(MP4Cover(artwork, MP4Cover.FORMAT_PNG))
				else:
					covr.append(MP4Cover(artwork, MP4Cover.FORMAT_JPEG))

				audio.tags['covr'] = covr
			elif audio_file.endswith('mp3'):
				audio = MP3(audio_file, ID3=ID3)

				# Add ID3 tags if they don't exist
				try:
					audio.add_tags()
				except error:
					pass

				audio.tags.add(
					APIC(
						encoding = 3, # 3 is UTF-8
						mime     = mimetype,
						type     = 3, # 3 is for cover artwork
						desc     = desc,
						data     = artwork))
			elif audio_file.endswith('flac'):
				audio = FLAC(audio_file)

				image = Picture()
				image.type = 3 # 3 is for cover artwork
				image.mime = mimetype
				image.desc = desc
				image.data = artwork

				audio.clear_pictures() # Clear existing pictures
				audio.add_picture(image)

		# Save the audio file
		audio.save()
