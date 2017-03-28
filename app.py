import concurrent.futures
import MySQLdb
import markdown
import os.path
import re
import subprocess
import torndb
import tornado.escape
from tornado import gen
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import unicodedata
import json
import redis

from tornado.options import define, options
from configparser import ConfigParser

from helper import AppHelper

from controllers import home
from controllers import user
from controllers import songs
from controllers import radio


db_config = ConfigParser()
db_config.read("grudio_db.ini")

define("mode", default="dev", help="development mode or production mode")
define("port", default=8888, help="run on the given port", type=int)
define("mysql_host", default=db_config["mysql"]["host"], help="mysql database host")
define("mysql_database", default=db_config["mysql"]["database"], help="mysql database name")
define("mysql_user", default=db_config["mysql"]["username"], help="mysql database user")
define("mysql_password", default=db_config["mysql"]["password"], help="mysql database password")

define("redis_host", default=db_config["redis"]["host"], help="redis database host")

define("redis_port", default=db_config["redis"]["port"], help="redis database host")

# A thread pool to be used for password hashing with bcrypt.
executor = concurrent.futures.ThreadPoolExecutor(2)


class Application(tornado.web.Application, AppHelper):
	def __init__(self):
		songs_path=os.path.join(os.path.dirname(__file__), "songs")
		handlers = [
			(r"/", home.Index),
			(r"/user/create", user.Signup),
			(r"/user/login", user.Login),
			(r"/user/logout", user.Logout),
			(r"/songs/addNew/([0-9]+)", songs.AddNewSong),
			(r"/songs/verify", songs.OnSongVerify),
			(r'/songs/(.*)', tornado.web.StaticFileHandler, {'path': songs_path}),
			(r"/radio/([a-z-]+)/([0-9]+)", radio.Home),
			(r"/radio", radio.Home),
			(r"/radio/playlist", radio.Playlist),
			(r"/radio/playlist/polling", radio.PlaylistPolling),
		]
		settings = dict(
			blog_title=u"Tornado Blog",
			template_path=os.path.join(os.path.dirname(__file__), "templates"),
			static_path=os.path.join(os.path.dirname(__file__), "static"),
			songs_path=os.path.join(os.path.dirname(__file__), "songs"),
			# ui_modules={"Entry": EntryModule},
			xsrf_cookies=True,
			# autoescape=False,
			cookie_secret="__TODO:_GENERATE_YOUR_OWN_RANDOM_VALUE_HERE__",
			login_url="/user/login",
			debug=True,
		)
		super(Application, self).__init__(handlers, **settings)

		self.mode = options.mode

		# Have one global connection to the blog DB across all handlers
		self.db = torndb.Connection(
			host=options.mysql_host, database=options.mysql_database,
			user=options.mysql_user, password=options.mysql_password)

		self.redis = redis.StrictRedis(host=options.redis_host, port=options.redis_port, db=0)

		with open("config.json") as json_file:
				self.config = json.load(json_file)

		self.initializePlaylist()



	def initializePlaylist_depricated(self):
		sql = '''
			SELECT category_id,
			       user_id,
			       name,
			       length,
			       file_path,
			       access_token,
			       score
			FROM songs c
			WHERE file_path IS NOT NULL
			  AND status = "not_played"
			GROUP BY category_id,
			         score
			HAVING
			  (SELECT COUNT(*)
			   FROM songs
			   WHERE category_id = c.category_id
			     AND score > c.score ) < 3
			ORDER BY category_id,
			         score DESC
		'''

		#sql = "select category_id, score from songs c group by category_id, score having ( select count(*) from songs where category_id = c.category_id and score > c.score) < 3 order by category_id, score desc"
		songs = self.db.query(sql)
		for song in songs:
			print song["score"]
			#print song["length"]



def main():
	tornado.options.parse_command_line()
	http_server = tornado.httpserver.HTTPServer(Application())
	http_server.listen(options.port)
	tornado.ioloop.IOLoop.current().start()


if __name__ == "__main__":
	main()