import discord_logging

import static
import utils
from classes.enums import ReturnType

log = discord_logging.get_logger()


class User:
	def __init__(self, name, created_utc=None):
		self.name = name
		self.created_utc = created_utc


class RedditObject:
	def __init__(
		self,
		body=None,
		author=None,
		created=None,
		id=None,
		permalink=None,
		link_id=None,
		prefix="t4",
		subreddit=None
	):
		self.body = body
		if isinstance(author, User):
			self.author = author
		else:
			self.author = User(author)
		if id is None:
			self.id = utils.random_id()
		else:
			self.id = id
		self.fullname = f"{prefix}_{self.id}"
		if created is None:
			self.created_utc = utils.datetime_now().timestamp()
		else:
			self.created_utc = created.timestamp()
		self.permalink = permalink
		self.link_id = link_id
		self.subreddit = subreddit

		self.parent = None
		self.children = []

	def get_pushshift_dict(self):
		return {
			'id': self.id,
			'author': self.author.name,
			'link_id': self.link_id,
			'body': self.body,
			'permalink': self.permalink,
			'created_utc': self.created_utc,
			'subreddit': self.subreddit
		}

	def get_first_child(self):
		if len(self.children):
			return self.children[0]
		else:
			return None

	def get_last_child(self):
		if len(self.children):
			return self.children[-1]
		else:
			return None

	def mark_read(self):
		return

	def reply(self, body):
		new_message = RedditObject(body, static.ACCOUNT_NAME)
		new_message.parent = self
		self.children.append(new_message)
		return new_message


class Reddit:
	def __init__(self, user):
		static.ACCOUNT_NAME = user
		self.sent_messages = []
		self.self_comments = []
		self.all_comments = {}
		self.users = {}
		self.banned_subreddits = set()
		self.locked_threads = set()
		self.pushshift_lag = 0

	def add_comment(self, comment, self_comment=False):
		self.all_comments[comment.id] = comment
		if self_comment:
			self.self_comments.append(comment)

	def add_user(self, user):
		self.users[user.name] = user

	def reply_message(self, message, body):
		self.sent_messages.append(message.reply(body))
		return ReturnType.SUCCESS

	def reply_comment(self, comment, body):
		if comment.subreddit is not None and comment.subreddit in self.banned_subreddits:
			return None, ReturnType.FORBIDDEN
		elif comment.link_id is not None and utils.id_from_fullname(comment.link_id) in self.locked_threads:
			return None, ReturnType.THREAD_LOCKED
		elif comment.id not in self.all_comments:
			return None, ReturnType.DELETED_COMMENT
		else:
			new_comment = comment.reply(body)
			self.add_comment(new_comment, True)
			return new_comment.id, ReturnType.SUCCESS

	def mark_read(self, message):
		message.mark_read()

	def send_message(self, username, subject, body):
		new_message = RedditObject(body, static.ACCOUNT_NAME)
		self.sent_messages.append(new_message)
		return ReturnType.SUCCESS

	def get_comment(self, comment_id):
		if comment_id in self.all_comments:
			return self.all_comments[comment_id]
		else:
			return RedditObject(id=comment_id)

	def edit_comment(self, body, comment=None, comment_id=None):
		if comment is None:
			comment = self.get_comment(comment_id)

		comment.body = body
		return ReturnType.SUCCESS

	def delete_comment(self, comment):
		if comment.id in self.all_comments:
			del self.all_comments[comment.id]
		try:
			self.self_comments.remove(comment)
		except ValueError:
			pass

		if comment.parent is not None:
			try:
				comment.parent.children.remove(comment)
			except ValueError:
				pass

		for child in comment.children:
			child.parent = None

		return True

	def ban_subreddit(self, subreddit):
		self.banned_subreddits.add(subreddit)

	def lock_thread(self, thread_id):
		self.locked_threads.add(thread_id)

	def get_user_creation_date(self, user_name):
		if user_name in self.users:
			return self.users[user_name].created_utc
		else:
			return None
