from flask import Flask, render_template, request, redirect, url_for, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user 
from werkzeug.security import generate_password_hash, check_password_hash 
from sqlalchemy import CheckConstraint
import os
import pyshorteners



app = Flask(__name__) 

#############################################
basedir = os.path.abspath(os.path.dirname(__file__)) 
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'data.sqlite') 
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False 
app.config['SECRET_KEY']='mykey'

db = SQLAlchemy(app)

Migrate( app, db) 


login_manager = LoginManager()
login_manager.init_app(app)

# Tell users what view to go to when they need to login.
login_manager.login_view = "login"


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(user_id)
##############################################

class User(db.Model, UserMixin): 
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True) 
    username = db.Column(db.String(9), unique = True, nullable = False) 
    password_hash = db.Column(db.String(64)) 
    name = db.Column(db.Text)
    __table_args__ = (
        CheckConstraint('LENGTH(username) >= 5 AND LENGTH(username)<=9'),
    )

    def __init__(self, username, password, name): 
        self.username = username 
        self.password_hash= generate_password_hash(password) 
        self.name = name
    
    def check_password(self, password): 
        return check_password_hash(self.password_hash, password)


class ShortURLPair(db.Model):
    __tablename__ = 'short_url_pairs'
    id = db.Column(db.Integer, primary_key=True)
    original_url = db.Column(db.String, nullable=False)
    short_url = db.Column(db.String, nullable=False)
    short_url_id = db.Column(db.Integer, db.ForeignKey('short_urls.id'))
    short_url_obj = db.relationship('ShortURL', backref=db.backref('url_pairs'))

class ShortURL(db.Model, UserMixin):
    __tablename__ = 'short_urls'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    user = db.relationship('User', backref=db.backref('short_urls'))

    @classmethod
    def add_or_update(cls, user_id, original_url, short_url):
        obj = cls.query.filter_by(user_id=user_id).first()
        if obj:
            pair = ShortURLPair(original_url=original_url, short_url=short_url, short_url_obj=obj)
            db.session.add(pair)
        else:
            obj = cls(user_id=user_id)
            db.session.add(obj)
            pair = ShortURLPair(original_url=original_url, short_url=short_url, short_url_obj=obj)
            db.session.add(pair)
        db.session.commit()
        return obj

    def get_url_pairs(self):
        return self.url_pairs.all()
   
################################################################## 

@app.route('/')
def home():
    return render_template('home.html') 

@app.route('/register', methods=['GET','POST'])
def register(): 
    if request.method == 'POST':
        name = request.form.get('name')
        username= request.form.get('username') 
        password= request.form.get('password') 
        confirm_password = request.form.get('confirm_password')
        # Checking if username is of valid length
        if len(username)>=5 and len(username)<=9:
            #checking if both passwords match
            if password == confirm_password: 
                # if username is available
                if not User.query.filter_by(username = username).first():
                    user = User(username,password, name)
                    db.session.add(user)
                    db.session.commit()
                    return redirect(url_for('login'))
                #if username is not avilable
                else: 
                    return render_template('register.html', username_exists = username) 
            #if passwords does not match
            else: 
                return render_template('register.html', password = password) 
        #if username is of invalid length and passwords do not match
        elif password is not confirm_password:
            return render_template('register.html', username = username, password = password) 
    return render_template('register.html') 

@app.route('/login', methods=['GET', 'POST'])
def login(): 
    if request.method == 'POST': 
        user = User.query.filter_by(username = request.form.get('username')).first() 
        if user is not None and user.check_password(request.form.get('password')):
            login_user(user)
            next = request.args.get('next') 
            if next == None or not next[0] == '/': 
                return render_template('home.html', name = user.name)
            return redirect(next) 
        else: 
            return render_template('login.html', credentials = user)
    return render_template('login.html')

@app.route('/shorten', methods = ['GET','POST'])
@login_required 
def shorten(): 
    if request.method == 'POST': 
        type_tiny = pyshorteners.Shortener()
        long_url = request.form.get('long_url')
        exist = ShortURLPair.query.filter_by(original_url = long_url, short_url_id = current_user.id).first()
        if exist:
            return render_template('shorten.html', name=current_user.name)
        short_url = type_tiny.tinyurl.short(long_url) 
        short_url_obj = ShortURL.add_or_update(current_user.id, long_url, short_url)
        return render_template('shorten.html', name=current_user.name, short_url=short_url)
    return render_template('shorten.html', name=current_user.name)
    

@app.route('/shortend_urls', methods= ['GET'])
@login_required
def shortened_urls(): 
    short_urls = ShortURLPair.query.filter_by(short_url_id=current_user.id).all()
    return render_template('shortURLS.html', short_urls = short_urls, name = current_user.name)

@app.route('/logout')
@login_required 
def logout(): 
    logout_user()
    return redirect(url_for('home'))

