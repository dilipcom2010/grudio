import json

class AppHelper:
	def initializePlaylist(self):
		redis_data = []

		categories = self.db.query("SELECT id FROM category WHERE 1")

		for category in categories:
			sql = '''
				SELECT s.id,
				       s.category_id,
				       s.user_id,
				       u.name as added_by,
				       s.name,
				       s.length,
				       s.file_path,
				       s.thumbnail,
				       s.access_token as token,
				       s.score
				FROM songs s, users u
				WHERE s.file_path IS NOT NULL
				  AND s.status="not_played"
				  AND s.category_id=%s
				  AND s.user_id=u.id
				ORDER BY score DESC LIMIT 3
			'''

			# sql = '''
			# 	SELECT id,
			# 	       category_id,
			# 	       user_id,
			# 	       name,
			# 	       length,
			# 	       file_path,
			# 	       thumbnail,
			# 	       access_token,
			# 	       score
			# 	FROM songs
			# 	WHERE file_path IS NOT NULL
			# 	  AND status="not_played"
			# 	  AND category_id=%s
			# 	ORDER BY score DESC LIMIT 3
			# '''

			songs = self.db.query(sql, category["id"])

			for i, song in enumerate(songs, 1):
				expiry = None

				if i==1:
					status = "playing"
					expiry = int(song["length"])
				elif i==2:
					status = "next"
				else:
					status = "queue"

				if status == "playing":
					sql = "UPDATE songs SET status='played', last_played=CURRENT_TIMESTAMP WHERE id=%s"
				else:
					sql = "UPDATE songs SET status='played' WHERE id=%s"

				updated = self.db.execute(sql, song["id"])
				updated = 1
				if updated:
					redis_key = "cat_"+str(category["id"])+"_"+status
					redis_value = {}
					
					redis_value["id"] = song["id"]
					redis_value["user_id"] = song["user_id"]
					redis_value["name"] = song["name"]
					redis_value["added_by"] = song["added_by"]

					redis_value["file_path"] = self.config[self.mode]["host"]+song["file_path"]
					redis_value["thumbnail"] = song["thumbnail"]
					redis_value["length"] = song["length"]
					redis_value["token"] = song["token"]

					redis_data.append({"key":redis_key, "value":json.dumps(redis_value), "expiry":expiry})

		self.redis_set_bulk(redis_data)

	def redis_set_bulk(self, datas):
		for data in datas:
			self.redisdb.set(data["key"], data["value"], data["expiry"])