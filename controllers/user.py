import bcrypt
import tornado.escape
from tornado import gen
import concurrent.futures
from basehandler import BaseHandler


executor = concurrent.futures.ThreadPoolExecutor(2)




class Signup(BaseHandler):
	def get(self):
		if self.get_secure_cookie("user"):
			self.redirect("/")
			return
		self.render("signup.html")

	@gen.coroutine
	def post(self):
		if self.get_secure_cookie("user"):
			self.redirect("/")
			return
		
		name = self.get_argument("name")
		email = self.get_argument("email")
		password = self.get_argument("password")
		confirm_password = self.get_argument("confirm_password")

		if password != confirm_password:
			raise tornado.web.HTTPError(400, "Password and confirm password should be same")

		if not name or not email or not password:
			raise tornado.web.HTTPError(400, "Please enter all fields")
		if self.user_exists(email):
			raise tornado.web.HTTPError(400, "This email already registered")
		
		hashed_password = yield executor.submit(
			bcrypt.hashpw, tornado.escape.utf8(password),
			bcrypt.gensalt())
		
		user_id = self.db.execute(
			"INSERT INTO users (name, email, password) "
			"VALUES (%s, %s, %s)",
			name, email, hashed_password)
		
		self.set_secure_cookie("user", str(user_id))
		self.redirect(self.get_argument("next", "/"))




class Login(BaseHandler):
	def get(self):
		# If there are no authors, redirect to the account creation page.
		if self.get_secure_cookie("user"):
			self.redirect("/")
			return

		if not self.any_user_exists():
			self.redirect("/user/create")
		else:
			self.render("login.html", error=None)

	@gen.coroutine
	def post(self):
		user = self.db.get("SELECT * FROM users WHERE email = %s", self.get_argument("email"))
		
		if not user:
			self.render("login.html", error="User is not registered. Please signup")
			return
		
		hashed_password = yield executor.submit(
			bcrypt.hashpw, tornado.escape.utf8(self.get_argument("password")),
			tornado.escape.utf8(user.password))
		
		if hashed_password == user.password:
			self.set_secure_cookie("user", str(user.id))
			self.redirect(self.get_argument("next", "/"))
		else:
			self.render("login.html", error="incorrect password")




class Logout(BaseHandler):
	def get(self):
		self.clear_cookie("user")
		self.redirect(self.get_argument("next", "/"))