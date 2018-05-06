import json
import math
from flask import Flask, request, jsonify, render_template, redirect
from flask_httpauth import HTTPBasicAuth

from db_connection import db
from db_connection import create_user, validate_user, user_is_admin, \
                          create_client, create_ad, get_closest_ads, \
                          list_ads, list_clients, list_users, valid_key

def to_float(s):
    try:
        n = float(s)
    except (TypeError, ValueError):
        return None
    if math.isnan(n):
        return None
    return n

DIST_TH = 50  # Threshold of 50 m to see the ad

app = Flask(__name__)
auth = HTTPBasicAuth()
# Add db
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///arado.db3"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db.app = app
db.init_app(app)


@app.route("/get_ads_location", methods=["POST"])
def get_ads_location():
    auth = request.headers.get("Authentication")
    if auth is None or not isinstance(auth, str):
        return jsonify({"error": "Invalid authentication"})
    
    token = auth[auth.find("Bearer ")+len("Bearer "):]
    if not valid_key(token):
        return jsonify({"error": "Invalid authentication"})

    latitude = to_float(request.values.get("latitude"))
    longitude = to_float(request.values.get("longitude"))

    if latitude is None or longitude is None:
        if request.data:
            # From requests from the app, I could only get the data here
            data = json.loads(request.data.decode("utf-8"))
            latitude = to_float(data.get("latitude"))
            longitude = to_float(data.get("longitude"))
            if latitude is None or longitude is None:
                return jsonify({"error": "Invalid coordinates"})
        else:
            return jsonify({"error": "Invalid coordinates"})
    
    closest = get_closest_ads((latitude, longitude), DIST_TH)
    return jsonify({"ads": closest})

@auth.verify_password
def verify_pw(username, password):
    """Validate user login"""
    return validate_user(username, password) and user_is_admin(username)


@app.route("/new_ad", methods=["GET", "POST"])
@auth.login_required
def insert_ad():
    """Insert ad page"""
    if request.method == "POST":
        ad_name = request.form.get("ad_name", "")
        client_name = request.form.get("client_name", "")
        ad_category = request.form.get("ad_category", "")
        ad_type = request.form.get("ad_type", "")
        latitude = to_float(request.form.get("latitude"))
        longitude = to_float(request.form.get("longitude"))
        height = to_float(request.form.get("ad_height"))

        if latitude is None or longitude is None or height is None:
            return render_template("new_ad.html", clients=list_clients(),
                                   error="Invalid coordinates")
        if create_ad(ad_name, client_name, latitude, longitude,
                     height, ad_category, ad_type) is False:
            # Error inserting on db
            return render_template("new_ad.html", clients=list_clients(),
                                   error="An error happened")
        return redirect("/")
    else:
        return render_template("new_ad.html", clients=list_clients(),
                               error="")


@app.route("/new_client", methods=["GET", "POST"])
@auth.login_required
def insert_client():
    """Insert client page"""
    if request.method == "POST":
        client_name = request.form.get("client_name", "")
        client_type = request.form.get("client_type", "")

        if client_type not in ["paid", "trial", "demo"]:
            return render_template("new_client.html", client_name=client_name,
                                   error="Invalid type")
        if create_client(client_name, client_type) is False:
            # Name already in use
            return render_template("new_client.html", client_name=client_name,
                                   error="Client name already in use")
        return redirect("/")
    else:
        return render_template("new_client.html", client_name="", error="")


@app.route("/new_user", methods=["GET", "POST"])
@auth.login_required
def insert_user():
    """Insert user page"""
    if request.method == "POST":
        username = request.form.get("username", "")
        password = request.form.get("password", "")
        email = request.form.get("email", "")
        is_admin = request.form.get("is_admin", "") == "on"

        if not password:
            return render_template("new_user.html", username=username,
                                   error="Invalid password")
        if create_user(username, password, email, is_admin) is False:
            # Name already in use
            return render_template("new_user.html", client_name=username,
                                   error="Username already in use")
        return redirect("/")
    else:
        return render_template("new_user.html", username="", error="")


@app.route("/list_ads", methods=["GET"])
@auth.login_required
def show_ads_list():
    """Ad list page"""
    return render_template("list_ads.html", ads=list_ads())


@app.route("/list_clients", methods=["GET"])
@auth.login_required
def show_clients_list():
    """Client list page"""
    return render_template("list_clients.html", clients=list_clients())


@app.route("/list_users", methods=["GET"])
@auth.login_required
def show_users_list():
    """Client list page"""
    return render_template("list_users.html", users=list_users())


@app.route("/", methods=["GET"])
@auth.login_required
def index():
    """Load main page"""
    return render_template("index.html")

if __name__ == "__main__":
    app.run()
