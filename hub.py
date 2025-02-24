from flask import Flask, request, render_template, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS  # Import CORS
import json
import datetime
import requests

db = SQLAlchemy()

class Channel(db.Model):
    __tablename__ = 'channels'
    id = db.Column(db.Integer, primary_key=True)
    active = db.Column('is_active', db.Boolean(), nullable=False, server_default='1')
    name = db.Column(db.String(100, collation='NOCASE'), nullable=False)
    endpoint = db.Column(db.String(100, collation='NOCASE'), nullable=False, unique=True)
    authkey = db.Column(db.String(100, collation='NOCASE'), nullable=False)
    type_of_service = db.Column(db.String(100, collation='NOCASE'), nullable=False)
    last_heartbeat = db.Column(db.DateTime(), nullable=True, server_default=None)

class ConfigClass(object):
    """ Flask application config """
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'
    SQLALCHEMY_DATABASE_URI = 'sqlite:///chat_server.sqlite'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

app = Flask(__name__)
app.config.from_object(__name__ + '.ConfigClass')
db.init_app(app)
CORS(app)  # Enable CORS for all routes
app.app_context().push()
db.create_all()

SERVER_AUTHKEY = '1234567890'

@app.route('/')
def home_page():
    channels = Channel.query.all()
    return render_template("home.html")

def health_check(endpoint, authkey):
    response = requests.get(endpoint + '/health',
                            headers={'Authorization': 'authkey ' + authkey})
    if response.status_code != 200:
        return False
    if 'name' not in response.json():
        return False
    channel = Channel.query.filter_by(endpoint=endpoint).first()
    if not channel:
        print(f"Channel {endpoint} not found in database")
        return False
    expected_name = channel.name
    if response.json()['name'] != expected_name:
        return False
    channel.last_heartbeat = datetime.datetime.now()
    db.session.commit()
    return True

@app.route('/channels', methods=['POST'])
def create_channel():
    global SERVER_AUTHKEY
    record = json.loads(request.data)
    if 'Authorization' not in request.headers:
        return "No authorization header", 400
    if request.headers['Authorization'] != 'authkey ' + SERVER_AUTHKEY:
        return "Invalid authorization header ({})".format(request.headers['Authorization']), 400
    if 'name' not in record:
        return "Record has no name", 400
    if 'endpoint' not in record:
        return "Record has no endpoint", 400
    if 'authkey' not in record:
        return "Record has no authkey", 400
    if 'type_of_service' not in record:
        return "Record has no type of service representation", 400

    update_channel = Channel.query.filter_by(endpoint=record['endpoint']).first()
    print("update_channel: ", update_channel)
    if update_channel:
        update_channel.name = record['name']
        update_channel.authkey = record['authkey']
        update_channel.type_of_service = record['type_of_service']
        update_channel.active = False
        db.session.commit()
        if not health_check(record['endpoint'], record['authkey']):
            return "Channel is not healthy", 400
        return jsonify(created=False, id=update_channel.id), 200
    else:
        channel = Channel(name=record['name'],
                          endpoint=record['endpoint'],
                          authkey=record['authkey'],
                          type_of_service=record['type_of_service'],
                          last_heartbeat=datetime.datetime.now(),
                          active=True)
        db.session.add(channel)
        db.session.commit()
        if not health_check(record['endpoint'], record['authkey']):
            db.session.delete(channel)
            db.session.commit()
            return "Channel is not healthy", 400
        return jsonify(created=True, id=channel.id), 200

@app.route('/channels', methods=['GET'])
def get_channels():
    channels = Channel.query.all()
    return jsonify(channels=[{'name': c.name,
                              'endpoint': c.endpoint,
                              'authkey': c.authkey,
                              'type_of_service': c.type_of_service} for c in channels]), 200

if __name__ == '__main__':
    app.run(port=5555, debug=True)