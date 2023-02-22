####################################################################################################
# This a sample Flask app that uses the Zoom API to list all of the archive files.
# It uses the OAuth flow to authenticate the user and then uses the access token
# which is stored in a session variable, to make requests to the Zoom API.
# The limitation of this app is that it only allows us to view the archive files in the past 7 days.
# @author: Yavik Kapadia
####################################################################################################

import importlib
import subprocess

packages = ["flask", "requests", "urllib", "pytz", "datetime", "uuid", "pandas"]
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
from datetime import datetime, timezone, timedelta
import pandas as pd

REDIRECT_URI = (
    "http://localhost:65010/zoom_callback"  # This must match your app's settings
)
CLIENT_ID = None # This is your app's client ID
CLIENT_SECRET = None # This is your app's client secret
SECRET_TOKEN = None  # This is your app's secret token


# Session variables
authenticated = False
access_token = None
next_page = False
next_page_token = None
json_data = None


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
    
    code = request.args.get("code")
    access_token = get_token(code)
    authenticated = True
    data = get_archive_files(access_token)

    if authenticated:  # if already authenticated, just show the archive
        return render_template(
            "archive.html",
            access_token=access_token,
            next_page=next_page,
            data=data,
        )

    
    
    
    # Note: In most cases, you'll want to store the access token, in, say,
    # a session for use in other parts of your web app.

    return render_template(
        "archive.html",
        access_token=access_token,
        next_page=next_page,
        data=data  
    )
   


# process form data from archive.html template
# convert time to zulu time
# get data from zoom api
# show data in archive.html template
@app.route("/archive/dates", methods=["GET"])
def archive_for_dates():
    # get the values from the form's input fields

    global access_token
    global next_page
    global next_page_token
    response = request.form  # get form data
    from_date = request.args.get("from_date")
    to_date = request.args.get("to_date")
    

    from_date_zulu = datetime.strptime(from_date, "%Y-%m-%d").strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )

    to_date_zulu = datetime.strptime(to_date, "%Y-%m-%d").strftime(
        "%Y-%m-%dT%H:%M:%SZ"
    )
    me_json = get_archive_files(access_token, from_date_zulu, to_date_zulu)

    return render_template(
        "archive.html", access_token=access_token, next_page=next_page, data=me_json
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

    return token_json["access_token"]
from datetime import datetime, timezone, timedelta
import requests


def get_archive_files(access_token, page_size=300, from_date=None, to_date=None):
    headers = {"Authorization": "Bearer " + access_token}
    params = {"page_size": page_size}

    # Use today - 7 days as default from_date and to_date if not provided
    if from_date is None:
        from_date = datetime.now(timezone.utc) - timedelta(days=7)
        from_date = from_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    if to_date is None:
        to_date = datetime.now(timezone.utc)
        to_date = to_date.strftime('%Y-%m-%dT%H:%M:%SZ')

    params["from"] = from_date
    params["to"] = to_date

    all_records = []
    next_page_token = ''
    while True:
        if next_page_token != '' or next_page_token != None:
            params["next_page_token"] = next_page_token

        response = requests.get(
            "https://api.zoom.us/v2/archive_files", params=params, headers=headers
        )
        if response.status_code == 200:
            me_json = response.json()
            
            all_records.extend(me_json.get("meetings"))
            
            print("total_records: " + str(len(all_records)))
            if me_json["next_page_token"] != '':
                next_page_token = me_json["next_page_token"]
                print("next_page_token: " + next_page_token)
            else:
                break
        else:
            print(response.status_code)
            print(response.text)
            break

    json_data = {
        "from": from_date,
        "to": to_date,
        "page_size": page_size,
        "total_records": len(all_records),
        "meetings": all_records
    }
    return json_data


def write_to_txt(data, filename="data.txt"):
    with open(filename, "w") as f:
        f.write(str(data))


def json_to_csv(data):
    csv = pd.read_json(data)
    csv = csv.to_csv("data.csv", index=False)

    with open("data.csv", "w") as f:
        f.write(str(csv))


if __name__ == "__main__":
    app.run(debug=True, port=65010)
