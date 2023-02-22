####################################################################################################
# This a sample Flask app that uses the Zoom API to list all of the archive files.
# It uses the OAuth flow to authenticate the user and then uses the access token
# which is stored in a session variable, to make requests to the Zoom API.
# The limitation of this app is that it only allows us to view the archive files in the past 7 days.
# @author: Yavik Kapadia
####################################################################################################

import importlib
import subprocess

packages = ["flask", "requests", "urllib", "pytz", "datetime"]
for package in packages:
    try:
        importlib.import_module(package)
        print(f"{package} is already installed")
    except ImportError:
        print(f"{package} is not installed. Installing now...")
        subprocess.check_call(["pip", "install", package])

from flask import Flask, abort, request, render_template
from uuid import uuid4
import requests
import requests.auth
import urllib
import datetime
from pytz import timezone

REDIRECT_URI = (
    "http://localhost:65010/zoom_callback"  # This must match your app's settings
)
CLIENT_ID = ""  # This is your app's client ID
CLIENT_SECRET = ""  # This is your app's client secret
SECRET_TOKEN = ""  # This is your app's secret token

# Session variables
authenticated = False
access_token = None
next_page = False
next_page_token = None

# Get data from 7 days ago
pastDate = datetime.datetime.now() - datetime.timedelta(days=7)
pastDataZuluTime = pastDate.strftime("%Y-%m-%dT%H:%M:%SZ")
nowzuluTime = datetime.datetime.now().strftime("%Y-%m-%dT%H:%M:%SZ")

# Create the Flask app
app = Flask(__name__, template_folder="templates", static_folder="static")


# Create the routes
@app.route("/")
def homepage():
    global authenticated
    global access_token
    global next_page
    if authenticated:
        return render_template(
            "archive.html",
            access_token=access_token,
            next_page=next_page,
            data=get_archive_files(access_token),
        )
    url = make_authorization_url()
    return render_template("index.html", url=url)


@app.route("/auth")
def make_authorization_url():
    params = {
        "client_id": CLIENT_ID,
        "response_type": "code",
        "redirect_uri": REDIRECT_URI,
    }
    url = "https://zoom.us/oauth/authorize?" + urllib.parse.urlencode(params)
    return url


@app.route("/zoom_callback")
def zoom_callback():
    global authenticated
    global access_token
    global next_page
    error = request.args.get("error", "")
    if error:
        return "Error: " + error

    if authenticated:  # if already authenticated, just show the archive
        return render_template(
            "archive.html",
            access_token=access_token,
            next_page=next_page,
            data=get_archive_files(access_token),
        )

    code = request.args.get("code")
    access_token = get_token(code)
    authenticated = True

    # Note: In most cases, you'll want to store the access token, in, say,
    # a session for use in other parts of your web app.

    return render_template(
        "archive.html",
        access_token=access_token,
        next_page=next_page,
        data=get_archive_files(access_token),
    )


# process form data from archive.html template
# convert time to zulu time
# get data from zoom api
# show data in archive.html template
@app.route("/archive_for_dates", methods=["GET"])
def archive_for_dates():
    # get the values from the form's input fields

    global access_token
    global next_page
    global next_page_token
    response = request.form  # get form data
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")

    from_date_zulu = datetime.datetime.strptime(from_date, "%Y-%m-%d").strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    print("from_date_zulu: ", from_date_zulu)
    to_date_zulu = datetime.datetime.strptime(to_date, "%Y-%m-%d").strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    print("to_date_zulu: ", to_date_zulu)

    headers = {"Authorization": "bearer " + access_token}
    response = requests.get(
        "https://api.zoom.us/v2/archive_files",
        params={"page_size": 300, "from": from_date_zulu, "to": to_date_zulu},
        headers=headers,
    )
    me_json = response.json()

    if len(me_json["next_page_token"]) != 0:
        next_page = True
        next_page_token = me_json["next_page_token"]
    print("next_page_token: ", next_page_token)
    return render_template(
        "archive.html", access_token=access_token, next_page=next_page, data=me_json
    )


@app.route("/next_page")
def get_next_page():
    global next_page
    global access_token
    global next_page_token
    headers = {"Authorization": "bearer " + access_token}
    response = requests.get(
        "https://api.zoom.us/v2/archive_files",
        params={
            "next_page_token": next_page_token,
            "page_size": 300,
            "from": pastDataZuluTime,
            "to": nowzuluTime,
        },
        headers=headers,
    )
    data = response.json()
    if len(data["next_page_token"]) != 0:
        next_page = True
        next_page_token = data["next_page_token"]
    else:
        next_page = False
    return render_template(
        "archive.html", access_token=access_token, next_page=next_page, data=data
    )


def get_token(code):
    client_auth = requests.auth.HTTPBasicAuth(CLIENT_ID, CLIENT_SECRET)
    post_data = {
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": REDIRECT_URI,
    }

    response = requests.post(
        "https://zoom.us/oauth/token", auth=client_auth, data=post_data
    )
    token_json = response.json()
    print(token_json)
    return token_json["access_token"]


def get_archive_files(access_token):
    global next_page
    global next_page_token
    headers = {"Authorization": "bearer " + access_token}
    response = requests.get(
        "https://api.zoom.us/v2/archive_files",
        params={"page_size": 300, "from": pastDataZuluTime, "to": nowzuluTime},
        headers=headers,
    )
    me_json = response.json()

    if len(me_json["next_page_token"]) != 0:
        next_page = True
        next_page_token = me_json["next_page_token"]
    print("next_page_token: ", next_page_token)
    return me_json


def write_to_txt(data):
    with open("data.txt", "w") as f:
        f.write(str(data))


if __name__ == "__main__":
    app.run(debug=True, port=65010)
