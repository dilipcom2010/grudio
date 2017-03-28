from basehandler import BaseHandler
import json
from traceback import format_exc


class Home(BaseHandler):
	def get(self, category_slug, category_id):
		categories = []
		recent_played_songs = []
		
		sql = "SELECT * FROM `category` WHERE id in (SELECT category_id FROM `songs` GROUP BY category_id HAVING COUNT(category_id)>2)"
		categories = self.db.query(sql)

		sql = "SELECT id, user_id, name, length, file_path, thumbnail, access_token as token FROM `songs` WHERE category_id=%s and status='played' and last_played IS NOT NULL ORDER BY last_played DESC LIMIT 1, 30"
		recent_played_songs = self.db.query(sql, category_id)

		self.render("radio.html", categories=categories, recent_played_songs=recent_played_songs, channelid=category_id)



class Playlist(BaseHandler):
	def get(self):
		result = {}
		error = None

		playlist_type = self.get_argument("type", None)
		category_id = self.get_argument("cat", None)

		if not playlist_type or not category_id:
			error = "Wrong Input"
		else:
			category_id = int(category_id)


		if not error:
			if playlist_type == "fresh":
				all_status = ["playing", "next", "queue"]
			elif playlist_type == "next":
				all_status = ["next"]
			else:
				result["error"] = "Wrong Input"

		if not error:
			playing = "cat_"+str(category_id)+"_playing"
			nextt = "cat_"+str(category_id)+"_next"
			queued = "cat_"+str(category_id)+"_queue"

			if not self.redis.get(playing):
				playing_song, next_song = self.redis.get(nextt), self.redis.get(queued)
				playing_song_detail = json.loads(playing_song)

				queued_song = self.getTopSongByCategory(category_id)
				
				if not queued_song:
					queued_song = self.getFallbackSong(category_id)
				
				queued_song = json.dumps(queued_song)
				try:
					expire = int(playing_song_detail["length"])				

					self.redis.set(playing, playing_song, expire)
					self.redis.set(nextt, next_song)
					self.redis.set(queued, queued_song)

					self.db.execute("UPDATE songs SET last_played=CURRENT_TIMESTAMP WHERE id=%s", playing_song_detail["id"])
				except:
					error = "Not able to get next song, may be songs list less than 3 in this category"


			if playlist_type=="next":
				result["next"] = json.loads(self.redis.get(nextt))
			else:
				playing_song = json.loads(self.redis.get(playing))
				playing_song["remaining"] = int(self.redis.ttl(playing))
				result["playing"] = playing_song
				result["next"] = json.loads(self.redis.get(nextt))
				result["queued"] = json.loads(self.redis.get(queued))



		jsonp = self.to_json(result)
		print jsonp
		self.set_header('Content-Type', 'application/javascript')
		self.write(jsonp);


	def getTopSongByCategory(self, category_id):
		sql = '''
				SELECT s.id,
				       s.user_id,
				       u.name as added_by,
				       s.name,
				       s.length,
				       s.file_path,
				       s.thumbnail,
				       s.access_token as token
				FROM songs s, users u
				WHERE s.file_path IS NOT NULL
				  AND s.status="not_played"
				  AND s.category_id=%s
				  AND s.user_id=u.id
				ORDER BY s.score DESC LIMIT 1
			'''

		song = self.db.get(sql, category_id)
		if song:
			self.db.execute("UPDATE songs SET status='played' WHERE id=%s", song["id"])
			song["file_path"] = self.config[self.mode]["host"]+song["file_path"]
		
		return song


	def getFallbackSong(self, category_id):
		sql = '''
				SELECT s.id,
				       s.user_id,
				       u.name as added_by,
				       s.name,
				       s.length,
				       s.file_path,
				       s.thumbnail,
				       s.access_token as token
				FROM songs s, users u
				WHERE s.file_path IS NOT NULL
				  AND s.category_id=%s
				  AND s.user_id=u.id
				ORDER BY RAND() LIMIT 1
			'''

		song = self.db.get(sql, category_id)
		song["file_path"] = self.config[self.mode]["host"]+song["file_path"]
		return song






class PlaylistPolling(BaseHandler):
	def get(self):
		result = {"error":None, "success":False}
		result["error"] = self._validateInput()
		
		if not result["error"]:
			action_type = self.get_argument("type")
			score = int(self.get_argument("count"))
			songid = int(self.get_argument("songid"))

			redis_key = str(self.get_secure_cookie("user")) + "_" + str(songid)
			redis_value = True

			if action_type == self.config["downvote_slug"]:
				score = -score
				redis_value = False
			try:
				self.db.execute("UPDATE songs SET score=score+%s WHERE id=%s", score, songid)
				self.redis.set(redis_key, redis_value, self.config["track_rating_action_lock_period"])
				result["success"] = True
			except:
				print format_exc()
				result["error"] = "Internal issue. Please try after sometime"


		jsonp = self.to_json(result)
		self.set_header('Content-Type', 'application/javascript')
		self.write(jsonp)


	def _validateInput(self):
		error = None

		loggedin_user_id = self.get_secure_cookie("user")
		if not loggedin_user_id:
			return "User not logged in"

		songid = self.get_argument("songid", None)
		token = self.get_argument("token", None)
		poll_type = self.get_argument("type", None)
		poll_count = int(self.get_argument("count", 0))



		if not songid or not token or not poll_type or not poll_count or (poll_type != self.config["upvote_slug"] and poll_type != self.config["downvote_slug"]):
			return "Invalid input"
		elif poll_type==self.config["upvote_slug"] and poll_count>self.config["max_upvote_points"]:
			return self.config["upvote_max_limit_msg"]
		elif poll_type==self.config["downvote_slug"] and poll_count>self.config["max_downvote_points"]:
			return self.config["downvote_max_limit_msg"]
		elif poll_count < 1:
			return self.config["polling_count_min_msg"]

		
		if not bool(self.db.get("SELECT * FROM songs WHERE id=%s AND access_token=%s", int(songid), token)):
			return "Not a valid song"

		redis_key = str(loggedin_user_id)+"_"+str(songid)
		if self.redis.get(redis_key) and self.redis.ttl(redis_key)>self.config["track_lock_gap"]:
			ttl = self.redis.ttl(redis_key)
			hour = ttl/3600
			minute = (ttl%3600)/60
			seconds = (ttl%3600)%60

			wait_time = str(hour)+" hours "+str(minute)+" minutes "+str(seconds)+" seconds"

			return "You have already actioned on this song. You can action again only after "+wait_time

		return error