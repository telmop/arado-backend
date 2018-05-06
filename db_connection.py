import hashlib
import random
import string

from flask_sqlalchemy import SQLAlchemy
import sqlalchemy
from geopy.distance import vincenty

KEY_LEN = 40
SALT_LEN = 5

def sha1(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()

def random_string(length):
    return "".join(random.choices(string.ascii_letters+string.digits,
                k=length))  

def gen_api_key():
    return random_string(KEY_LEN)

def gen_salt():
    return random_string(SALT_LEN)


db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(80), nullable=False)
    api_key = db.Column(db.String(80), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    email = db.Column(db.String(80))


class Client(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(80), unique=True, nullable=False)
    type = db.Column(db.String(80), nullable=False)
    balance = db.Column(db.Float)
    ads = db.relationship('Ad', backref='client', lazy=True)


class Ad(db.Model):
    id = db.Column(db.Integer, primary_key=True, unique=True)
    name = db.Column(db.String(80))  # Campaign name
    client_id = db.Column(db.Integer, db.ForeignKey('client.id'),
                          nullable=False)
    category = db.Column(db.String(80), nullable=False)
    latitude = db.Column(db.Float, nullable=False)
    longitude = db.Column(db.Float, nullable=False)
    height = db.Column(db.Float, default=0)
    views = db.Column(db.Integer, default=0)
    clicks = db.Column(db.Integer, default=0)
    type = db.Column(db.String(80))
    data = db.Column(db.LargeBinary)


def create_user(username, password, email="", is_admin=False):
    salt = gen_salt()
    api_key = gen_api_key()
    hashed_pw = salt + "|" + sha1(salt+password)
    user = User(username=username, password=hashed_pw, api_key=api_key,
                email=email, is_admin=is_admin)
    try:
        db.session.add(user)
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        # Invalid username
        return False
    return True


def user_is_admin(username):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return False
    return user.is_admin


def validate_user(username, password):
    user = User.query.filter_by(username=username).first()
    if user is None:
        return False
    hashed_pw = user.password
    salt, sha1_hash = hashed_pw.split("|")
    return sha1(salt + password) == sha1_hash


def valid_key(api_key):
    user = User.query.filter_by(api_key=api_key).first()
    if user is None:
        return False
    return True


def create_client(name, type, balance=0):
    client = Client(name=name, type=type, balance=balance)
    try:
        db.session.add(client)
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        # Name already in use
        return False
    return True


def create_ad(name, client_name, latitude, longitude, height,
              category, type, data=None):
    client = Client.query.filter_by(name=client_name).first()
    if client is None:
        return False
    ad = Ad(name=name, client_id=client.id, category=category,
            latitude=latitude, longitude=longitude, height=height,
            type=type, data=data)
    try:
        db.session.add(ad)
        db.session.commit()
    except sqlalchemy.exc.IntegrityError:
        # Invalid data
        return False
    return True


def list_ads():
    return Ad.query.all()


def list_clients():
    return Client.query.all()

def list_users():
    return User.query.all()


def get_closest_ads(location, threshold):
    closest_ads = []
    for ad in list_ads():
        ad_location = (ad.latitude, ad.longitude)
        if vincenty(location, ad_location).m <= threshold:
            closest_ads.append(ad_location)
            ad.views += 1
            db.session.commit()
    return closest_ads
