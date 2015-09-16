from flask.ext.login import UserMixin

class UserNotFoundError(Exception):
	"""Exception for when a user does not exist."""
	pass

class SoundBubbleUser(UserMixin):
	"""
	Represents a Sound Bubble user.
	A SoundBubbleUser object will need to be created
	before a user can be logged in.

	Properties:
		id (str):       The id for the user, in this case, their username.
		password (str): The password for the user.
	"""

	# Dict of all available users, as {user: pass}
	_users = {}

	def __init__(self, id):
		"""
		Initializes a new SoundBubbleUser if a user has the given id,
		otherwise a UserNotFoundError is raised.
		"""
		id = id.strip().lower()
		if not id in self._users:
			raise UserNotFoundError()
		self.id = id
		self.password = self._users[id]

	@classmethod
	def get(cls, id):
		"""
		Returns a SoundBubbleUser item for the given id,
		or None if that user does not exist.
		"""
		try:
			return cls(id)
		except UserNotFoundError:
			return None

	@classmethod
	def register_users(cls, new_users):
		"""
		Registers users which can be logged in.

		Arguments:
			new_users (dict): A dict of new users as {user: pass}
		"""
		cls._users = new_users
