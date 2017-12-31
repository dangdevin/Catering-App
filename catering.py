from flask import Flask, request, abort, url_for, redirect, session, escape, render_template, flash
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

### init

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///catering.db'
db = SQLAlchemy(app)

events = db.Table('events', db.Column('event_id', db.Integer, db.ForeignKey('event.id')), db.Column('staff_id', db.Integer, db.ForeignKey('staff.id')))

def get_date(timestamp):
	return datetime.utcfromtimestamp(timestamp).strftime('%Y-%m-%d')

### models

class Staff(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), nullable=False, unique=True)
	password = db.Column(db.String(10), nullable=False)
	account_type = db.Column(db.String(80))
	events = db.relationship('Event', secondary=events, lazy='dynamic', backref=db.backref('staffs', lazy='dynamic'))

	def __init__(self, username, password, account_type):
		self.username = username
		self.password = password
		self.account_type = account_type
		
	def __repr__(self):
		return '<Staff %r>' % self.username


class Customer(db.Model):
	id = db.Column(db.Integer, primary_key=True)
	username = db.Column(db.String(80), nullable=False, unique=True)
	password = db.Column(db.String(10), nullable=False)
	account_type = db.Column(db.String(80))
	events = db.relationship('Event', lazy='select', backref='customer')

	def __init__(self, username, password, account_type):
		self.username = username
		self.password = password
		self.account_type = account_type
		
	def __repr__(self):
		return '<Customer %r>' % self.username

class Event(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customer.id'), nullable=False)
    event_name = db.Column(db.String(50), nullable=False)
    event_site = db.Column(db.String(50), nullable=False)
    event_date = db.Column(db.String(20), nullable=False)
    staff_id_1 = db.Column(db.Integer, db.ForeignKey('staff.id'))
    staff_id_2 = db.Column(db.Integer, db.ForeignKey('staff.id'))
    staff_id_3 = db.Column(db.Integer, db.ForeignKey('staff.id'))

    def __init__(self, customer_id, event_name, event_site, event_date):
        self.customer_id = customer_id
        self.event_name = event_name
        self.event_site = event_site
        self.event_date = event_date

    def __repr__(self):
        return '<Event = %r %r %r %r %r>' % (self.id, self.customer_id,
                                             self.staff_id_1, self.staff_id_2, self.staff_id_3)

@app.cli.command('initdb')
def initdb_command():
	"""Reinitializes the database"""
	db.drop_all()
	db.create_all()

	print('Initialized the database.')


### routes

# by default, direct to login
@app.route("/")
def default():
	return redirect(url_for('logger'))
	
@app.route("/login/", methods=["GET", "POST"])
def logger():
	# first check if the user is already logged in
	if "username" in session:
		return redirect(url_for("profile", username=session["username"], account_type=session["account_type"]))

	# check for owner and redirect owner
	if request.method == "POST":
		current_user = request.form["user"]
		look_for_staff = Staff.query.filter_by(username=current_user).first()
		look_for_customer = Customer.query.filter_by(username=current_user).first()

		if request.form["user"] == "owner" and  request.form["pass"] == "pass":
			session["username"] = request.form["user"]
			session["account_type"] = "owner"
			return redirect(url_for("profile", username=request.form["user"], account_type="owner"))
		elif look_for_staff != None and request.form["user"] == look_for_staff.username and request.form["pass"] == look_for_staff.password:
			session["username"] = request.form["user"]
			session["account_type"] = "staff"
			return redirect(url_for("profile", username=request.form["user"], account_type="staff"))
		elif look_for_customer != None and request.form["user"] == look_for_customer.username and request.form["pass"] == look_for_customer.password:
			session["username"] = request.form["user"]
			session["account_type"] = "customer"
			return redirect(url_for("profile", username=request.form["user"], account_type="customer"))
		elif request.form["user"] == None:
			return redirect(url_for('logger'))
		elif request.form["pass"] == None:
			return redirect(url_for('logger'))
		else:
			return redirect(url_for('logger'))

	# if not, and the incoming request is via POST try to log them in
	#elif request.method == "POST":
	#	if request.form["user"] in users and users[request.form["user"]] == request.form["pass"]:
	#		session["username"] = request.form["user"]
	#		return redirect(url_for("profile", username=session["username"]))

	# if all else fails, offer to log them in
	elif request.method == "GET":
		return render_template("login.html")

@app.route("/profile/<account_type>/<username>")
def profile(username=None, account_type=None):
	if "username" in session:
		if username == None and account_type == None:
			return redirect(url_for('profile', username=session["username"], account_type=session["account_type"]))
		if session["username"] == "owner":
			return render_template('owner.html')
				
		#elif username == "owner"
			# if specified, check to handle users looking up their own profile
			#if username in session and session[username] == username:
			#	return ownerProfile.format(url_for("unlogger"))

		elif session["username"] == username:
			if account_type == "staff":
				return render_template('staff.html', name=username)
			elif account_type == "customer":
				right_now = format_datetime(time.time())
				return render_template('customer.html', name=username, date=right_now)
	abort(403)

@app.route("/logout/", methods=["GET", "POST"])
def unlogger():
	if "username" in session:
		session.clear()
		return redirect(url_for("logger"))

### methods

# allows owner to add staff
@app.route('/create-new-staff', methods=['POST', 'GET'])
def create_new_staff():
	if request.method == "GET":
		if "username" in session:
			if session["username"] == "owner":
				return render_template('create-new-staff.html', name='owner')
			else:
				abort(403)
	else:
		#reject if username is owner
		if request.form['user'] == "owner":
			return redirect(url_for('create_new_staff'))
		#search for existing username
		temp = Staff.query.filter_by(username=request.form['user']).first()
		#if unique username, add to database
		if temp == None:
			db.session.add(Staff(request.form["user"], request.form["pass"], "staff"))
			db.session.commit()
		else:
			return redirect(url_for('create_new_staff'))
		return redirect(url_for('profile', username=session['username'], account_type='owner'))

# allows customer to make new account
@app.route('/create-new-account', methods=['POST', 'GET'])
def create_new_account():
	if request.method == "GET":
		return render_template('create-new-account.html')
	else:
		# reject if username is owner
		if request.form['user'] == "owner":
			return redirect(url_for('create_new_account'))
		#search for existing username
		temp = Staff.query.filter_by(username=request.form['user']).first()
		#if unique username, add to database
		if temp == None:
			db.session.add(Customer(request.form["user"], request.form["pass"], "customer"))
			db.session.commit()
		else:
			return redirect(url_for('create_new_account'))
		return redirect(url_for('logger'))

@app.route('/book-an-event/')
@app.route('/book-an-event/<username>/<date>', methods=['GET', 'POST'])
def book_an_event(username=None, date=None):
	if request.method == "GET":
		return render_template("book-an-event.html", name=username, date=date)

	get_event = Event.query.filter_by(event_date = request.form["event_date"]).first()
	customer = Customer.query.filter_by(username=username).first()
	db.session.add(Event(customer.id, request.form["event_name"], request.form["event_site"], request.form["event_date"]))
	db.session.commit()
	return redirect(url_for('profile', username=customer.username, account_type="customer"))


# needed to use sessions
# note that this is a terrible secret key
app.secret_key = "this is a terrible secret key"
			
if __name__ == "__main__":
	app.run()

#input('Press ENTER to exit')
