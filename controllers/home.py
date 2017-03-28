import tornado.web
from basehandler import BaseHandler

class Index(BaseHandler):
	def get(self):
		# x = self.db.query("SELECT * FROM users WHERE 1")
		# print x
		self.render("index.html")