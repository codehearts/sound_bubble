from os import path, remove, makedirs
from musicgen import MusicGen
import unittest
import shutil

class MusicGenTests(unittest.TestCase):

	def setUp(self):
		self.musicgen     = MusicGen()
		self.filetypes    = ['mp3', 'm4a', 'flac']
		self.audio = {
			'mp3': {
				'cover':    'tests/audio/mp3/14 Betelgeuse_36.mp3',
				'no_cover': 'tests/audio/mp3/17 Eructation concertmatienne.mp3'
			},
			'm4a': {
				'cover':    'tests/audio/m4a/14 Betelgeuse_36.m4a',
				'no_cover': 'tests/audio/m4a/17 Eructation concertmatienne.m4a'
			},
			'flac': {
				'cover':    'tests/audio/flac/14 Betelgeuse_36.flac',
				'no_cover': 'tests/audio/flac/17 Eructation concertmatienne.flac'
			}
		}
		self.tmp_dir      = 'tests/tmp'
		self.out_file     = self.tmp_dir + '/out.jpg'
		self.art_file     = 'tests/artwork/art.png'

		if not path.exists(self.tmp_dir):
			makedirs(self.tmp_dir)

	def tearDown(self):
		# Delete the tmp directory
		shutil.rmtree('tests/tmp')

		if path.isfile(self.out_file):
			remove(self.out_file)

	def test_extract_cover_art_coverless(self):
		"""Tests extracting cover art from a file with no artwork."""

		for filetype in self.filetypes:
			self.assertIsNone(
				self.musicgen.extract_cover_art(self.audio[filetype]['no_cover']),
				'Coverless {} returned cover art data'.format(filetype))

			self.assertIsNone(
				self.musicgen.extract_cover_art(self.audio[filetype]['no_cover'], self.out_file),
				'Coverless {} returned cover art data when saving to file'.format(filetype))

			self.assertFalse(
				path.isfile(self.out_file),
				'Extracting from coverless {} file to output file created output file'.format(filetype))

	def test_extract_cover_art(self):
		"""Tests extracting cover art from a file with artwork."""

		for filetype in self.filetypes:
			self.assertIsNotNone(
				self.musicgen.extract_cover_art(self.audio[filetype]['cover']),
				'{} did not return cover art data'.format(filetype))

			self.assertIsNone(
				self.musicgen.extract_cover_art(self.audio[filetype]['cover'], self.out_file),
				'{} returned cover art data when saving to file'.format(filetype))

			self.assertTrue(
				path.isfile(self.out_file),
				'Extracting from {} file to output file did not create output file'.format(filetype))

			self.assertEqual(
				self.musicgen.extract_cover_art(self.audio[filetype]['cover']),
				open(self.out_file, 'rb').read(),
				'Saved {} cover art differs from embedded artwork'.format(filetype))

	def test_embed_cover_art_coverless(self):
		"""Tests embedding cover art in a coverless audio file with an image file."""

		for filetype in self.filetypes:
			# Copy the audio file to the tmp dir
			tmp_file = path.join(self.tmp_dir, path.basename(self.audio[filetype]['no_cover']))
			shutil.copyfile(self.audio[filetype]['no_cover'], tmp_file)

			self.assertEqual(
				self.musicgen.extract_cover_art(self.audio[filetype]['no_cover']),
				self.musicgen.extract_cover_art(tmp_file),
				'Copied {} cover art differs from original artwork'.format(filetype))

			self.musicgen.embed_cover_art(tmp_file, self.art_file)

			self.assertEqual(
				self.musicgen.extract_cover_art(tmp_file),
				open(self.art_file, 'rb').read(),
				'Newly embedded {} cover art is not same as cover art image file'.format(filetype))

			self.assertNotEqual(
				self.musicgen.extract_cover_art(self.audio[filetype]['cover']),
				self.musicgen.extract_cover_art(tmp_file),
				'Newly embedded {} cover art does not differ from original artwork'.format(filetype))

	def test_embed_cover_art(self):
		"""Tests embedding cover art in an audio file with an image file."""

		for filetype in self.filetypes:
			# Copy the audio file to the tmp dir
			tmp_file = path.join(self.tmp_dir, path.basename(self.audio[filetype]['cover']))
			shutil.copyfile(self.audio[filetype]['cover'], tmp_file)

			self.assertEqual(
				self.musicgen.extract_cover_art(self.audio[filetype]['cover']),
				self.musicgen.extract_cover_art(tmp_file),
				'Copied {} cover art differs from original artwork'.format(filetype))

			self.musicgen.embed_cover_art(tmp_file, self.art_file)

			self.assertEqual(
				self.musicgen.extract_cover_art(tmp_file),
				open(self.art_file, 'rb').read(),
				'Newly embedded {} cover art is not same as cover art image file'.format(filetype))

			self.assertNotEqual(
				self.musicgen.extract_cover_art(self.audio[filetype]['cover']),
				self.musicgen.extract_cover_art(tmp_file),
				'Newly embedded {} cover art does not differ from original artwork'.format(filetype))

if __name__ == '__main__':
    unittest.main()
