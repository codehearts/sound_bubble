from musicgen import MusicGen
from os import path, remove
import unittest

class MusicGenTests(unittest.TestCase):

	def setUp(self):
		self.musicgen     = MusicGen()
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
		self.art_file     = 'tests/tmp/out.jpg'

	def tearDown(self):
		if path.isfile(self.art_file):
			remove(self.art_file)

	def test_extract_cover_art_coverless(self):
		"""Tests extracting cover art from a file with no artwork."""

		for filetype in ['mp3', 'm4a', 'flac']:
			self.assertIsNone(
				self.musicgen.extract_cover_art(self.audio[filetype]['no_cover']),
				'Coverless {} returned cover art data'.format(filetype))

			self.assertIsNone(
				self.musicgen.extract_cover_art(self.audio[filetype]['no_cover'], self.art_file),
				'Coverless {} returned cover art data when saving to file'.format(filetype))

			self.assertFalse(
				path.isfile(self.art_file),
				'Extracting from coverless {} file to output file created output file'.format(filetype))

	def test_extract_cover_art(self):
		"""Tests extracting cover art from a file with artwork."""

		for filetype in ['mp3', 'm4a', 'flac']:
			self.assertIsNotNone(
				self.musicgen.extract_cover_art(self.audio[filetype]['cover']),
				'{} did not return cover art data'.format(filetype))

			self.assertIsNone(
				self.musicgen.extract_cover_art(self.audio[filetype]['cover'], self.art_file),
				'{} returned cover art data when saving to file'.format(filetype))

			self.assertTrue(
				path.isfile(self.art_file),
				'Extracting from {} file to output file did not create output file'.format(filetype))

			self.assertEqual(
				self.musicgen.extract_cover_art(self.audio[filetype]['cover']),
				open(self.art_file, 'rb').read(),
				'Saved {} cover art differs from embedded artwork'.format(filetype))

if __name__ == '__main__':
    unittest.main()
