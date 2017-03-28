import torndb
import json
import os
import pafy
import uuid

from traceback import format_exc

class MonitorPlaylist:
	def __init__(self):
		self.db = torndb.Connection(host="127.0.0.1", database="grudio", user="root", password="fyogi")
		self.projectDir = os.path.abspath(os.path.join(os.path.dirname(__file__), os.path.pardir))
		self.configFile = os.path.join(self.projectDir, "config.json")
		self.songsAbsDir = self.projectDir+"/songs"
		self.songsRelativeDir = "songs"

		self.next_playing_songs_ids = []


		with open(self.configFile) as json_file:
			self.config = json.load(json_file)





	def unlockSongs(self):
		try:
			sql = "UPDATE songs SET status='not_played' WHERE status='played' AND (UNIX_TIMESTAMP(CURRENT_TIMESTAMP)-UNIX_TIMESTAMP(last_played)) > %s"
			self.db.execute(sql, self.config["track_replay_lock"])
		except:
			print format_exc()




	def downloadNextPlayingRemoveExcept(self):
		category_ids = self.db.query("SELECT id FROM category WHERE 1")

		# next_playing_songs_ids = []
		if category_ids:
			for categoryid in category_ids:
				categoryid = categoryid["id"]
				total_runtime = 0

				next_playing_songs = self.db.query("SELECT * FROM songs WHERE status='not_played' AND category_id=%s ORDER BY score DESC", categoryid)
				total_runtime = self.updateNextPlayingSongs(next_playing_songs, total_runtime)
				
				if total_runtime < self.config["max_runtime_downloaded"]:
					next_playing_songs = self.db.query("SELECT * FROM songs WHERE status='played' AND category_id=%s ORDER BY score DESC", categoryid)
					total_runtime = self.updateNextPlayingSongs(next_playing_songs, total_runtime)


		self.deleteNotNextPlayingSongs()




	def downloadSong(self, url):
		p = pafy.new(url)
		download_link = p.getbestaudio(preftype='m4a', ftypestrict=True)

		print "downloading song..."
		old_file = download_link.download(quiet=True, filepath=self.songsAbsDir)
		print old_file
		filename, ext = os.path.splitext(old_file)

		unique_id = str(uuid.uuid4())
		new_file = self.songsAbsDir+"/"+unique_id+ext
		os.rename(old_file, new_file)

		song_relative_file = self.songsRelativeDir+"/"+unique_id+ext

		return song_relative_file





	def updateNextPlayingSongs(self, next_playing_songs, total_runtime):
		for next_song in next_playing_songs:
			if next_song["file_path"]:
				total_runtime += next_song["length"]
				self.next_playing_songs_ids.append(next_song["id"])
			else:
				file_path = self.downloadSong(next_song["url"])
				if file_path:
					try:
						self.db.execute("UPDATE songs SET file_path=%s WHERE id=%s", file_path, next_song["id"])
						total_runtime += next_song["length"]
						self.next_playing_songs_ids.append(next_song["id"])
					except:
						print format_exc()

			if total_runtime >= self.config["max_runtime_downloaded"]:
				break

		return total_runtime




	def deleteNotNextPlayingSongs(self):
		if self.next_playing_songs_ids:
			unwantedSongs = self.db.query("SELECT * FROM songs WHERE id NOT IN %s AND file_path IS NOT NULL", self.next_playing_songs_ids)
			
			deleted_songs_ids = []
			for song in unwantedSongs:
				try:
					song_file = self.projectDir+"/"+song["file_path"]
					os.remove(song_file)
					deleted_songs_ids.append(song["id"])
				except:
					print format_exc()

			if deleted_songs_ids:
				try:
					self.db.execute("UPDATE songs SET file_path=NULL WHERE id IN %s", deleted_songs_ids)
				except:
					print format_exc()


obj = MonitorPlaylist()
obj.unlockSongs()
obj.downloadNextPlayingRemoveExcept()