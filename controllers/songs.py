import tornado.web
from basehandler import BaseHandler
import pafy
from traceback import format_exc
from tornado import concurrent
import os, uuid

executor = concurrent.futures.ThreadPoolExecutor(8)

class AddNewSong(BaseHandler):
	@tornado.web.authenticated
	def get(self, catid):
		category = self.db.get("SELECT * FROM category WHERE id=%s", catid)
		if not category:
			self.set_status(400)
			self.finish("<html><body>Sorry this channel not available</body></html>")
		else:
			self.render("add_song.html", category=category)

	@tornado.web.authenticated
	def post(self, catid):
		self.catid = int(catid)
		result = {"error":None, "success":None}

		# if not self.get_secure_cookie("user"):
		# 	result["error"] = "User not logged in"
		# else:
		error = self._validateInput()
		if error:
			result["error"] = error

		if not result.get("error", None):
			error = self._validateSong()
			if error:
				result["error"] = error
			else:
				result["success"] = "Song submitted successfully, will be added soon."
				executor.submit(self._processSong)
				#self.write('request accepted')


		jsonp = self.to_json(result)
		self.set_header('Content-Type', 'application/javascript')
		self.write(jsonp)


	def _insertSong(self, data):
		print "inserting song..."
		try:
			song_id = self.db.execute(
				"INSERT INTO songs (name, audioid, user_id, initial_score, score, category_id, url, thumbnail, access_token, file_path, length) "
				"VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)",
				data["name"], data["audioid"], data["user_id"], data["initial_score"], data["score"], data["category_id"], data["url"], data["thumbnail"], data["access_token"], data["file_path"], data["length"])
			if song_id:
				print "insertion successfull"
				return song_id
		except:
			print format_exc()
			print "Insertion error"

		return None


	def _getInitialScore(self, likes, dislikes):
		return (likes/self.config["likes_per_point"]-dislikes/self.config["likes_per_point"])


	def _processSong(self):
		data = {}

		p = pafy.new(self.get_argument("url", None))
		download_link = p.getbestaudio(preftype='m4a', ftypestrict=True)

		print "downloading song..."
		old_file = download_link.download(quiet=True, filepath=self.settings["songs_path"])
		print old_file
		filename, ext = os.path.splitext(old_file)


		initial_score = self._getInitialScore(p.likes, p.dislikes)
		new_file = self.settings["songs_path"]+"/"+str(uuid.uuid4())+ext
		os.rename(old_file, new_file)


		data["name"] = self.get_argument("name", None)
		if not data["name"]:
			data["name"] = p.title
		data["audioid"] = p.videoid
		data["initial_score"] = initial_score
		data["category_id"] = self.catid
		data["url"] = self.get_argument("url")
		data["thumbnail"] = p.thumb
		data["access_token"] = str(uuid.uuid4())
		data["file_path"] = new_file
		data["length"] = int(p.length)
		data["user_id"] = int(self.get_secure_cookie("user"))
		data["score"] = self._getScore(data["category_id"], initial_score)
		

		self._insertSong(data)



	def _getScore(self, category_id, initial_score):
		try:
			score = self.db.get("SELECT score FROM songs WHERE initial_score>%s AND score>=%s AND category_id=%s ORDER BY initial_score ASC LIMIT 1", initial_score, initial_score, category_id)
		except:
			print format_exc()
		
		if score:
			return score["score"]
		else:
			return initial_score


	def _validateSong(self):
		error = None

		try:
			v = pafy.new(self.get_argument("url", None))

			ytube_category = v.category
			if ytube_category.upper() != "MUSIC":
				error = "Plese add MUSIC category only."
				return error

			if v.length < self.config["song_min_length"] or v.length > self.config["song_max_length"]:
				error = "song length should be between %s min to %s min" % (self.config["song_min_length"]/60, self.config["song_max_length"]/60)
				return error
			
			if v.likes >= self.config["likes_limit"] and v.dislikes >= self.config["dislike_limit"]:
				if (v.dislikes*100)/v.likes >= self.config["song_hate_ratio"]:
					error = "Song is not satisfying the popuraliry ratio"
					return error

			
			if self.user_already_added_song(v.videoid):
				error = "You have already added this song. Please visit profile section to check it."
				return error

			if not self._needdToAddSong(v.videoid):
				return "Song is already added in this category"
		
		except:
			error = "URL not valid"

		return error



	def _needdToAddSong(self, audioid):
		try:
			if self.db.get("SELECT * FROM songs WHERE audioid=%s AND category_id=%s LIMIT 1", audioid, self.catid):
				return False
		except:
			print format_exc()
			return False

		return True


	def _validateInput(self):
		loggedin_user = self.get_secure_cookie("user")
		songUrl = self.get_argument("url", None)

		error = False
		try:
			if not songUrl:
				return "URL of song or category can not be empty"
		except:
			return "Invalid input"

		return error



class OnSongVerify(BaseHandler):
	def get(self):
		result = {"error":"This service is not available now. Wait untill next release. Thanks!!!"}
		error, unverified_song = _validateInput()

		if not error:
			pass

		jsonp = self.to_json(result)
		self.set_header('Content-Type', 'application/javascript')
		self.write(jsonp)


	def _validateInput(self):
		song_id = int(self.get_argument("sid", 0))
		token = self.get_argument("token", None)
		if not song_id or not token:
			return "Invalid input", None

		user_id = self.get_secure_cookie("user")
		if not user_id:
			return "User not authenticated", None
		else:
			user_id = int(user_id)

		if not self.can_verify_song(user_id):
			return "You have not enough points to verify song", None

		unverified_song = self.db.get("SELECT * FROM unverified_songs WHERE id=%s AND token=%s LIMIT 1", song_id, token)
		if not unverified_song:
			return "No such song exist", None

		if unverified_song["added_by"] == user_id:
			return "You can not verify the song that is added by you", None


		return None, unverified_song