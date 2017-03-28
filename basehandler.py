import tornado.web
import json
from bson import json_util

class BaseHandler(tornado.web.RequestHandler):
	config = {}

	def set_default_headers(self):
		self.set_header("Access-Control-Allow-Origin", "*")

	@property
	def db(self):
		return self.application.db

	@property
	def redis(self):
		return self.application.redis

	@property
	def config(self):
		return self.application.config

	@property
	def mode(self):
		return self.application.mode

	def get_current_user(self):
		user_id = self.get_secure_cookie("user")
		if not user_id: return None
		return self.db.get("SELECT * FROM users WHERE id = %s", int(user_id))

	def any_user_exists(self):
		return bool(self.db.get("SELECT * FROM users LIMIT 1"))

	def user_exists(self, email):
		return bool(self.db.get("SELECT * FROM users WHERE email=%s", email))

	def user_already_added_song(self, songid):
		return bool(self.db.get("SELECT * FROM songs WHERE user_id=%s AND audioid=%s LIMIT 1", int(self.get_secure_cookie("user")), songid))
	
	
	def can_verify_song(self, user_id):
		points = self.db.get("SELECT points FROM users WHERE id=%s LIMIT 1", user_id)
		if points:
			points = point["points"]
		else:
			points = 0

		if points >= self.config["min_points_to_veriry_song"]:
			return True
		
		return False


	def to_json(self, data):
		try:
			data = json.dumps(data, default=json_util.default)
			data = json.loads(data)
		except:
			print format_exc()
			data = ''
		return data
