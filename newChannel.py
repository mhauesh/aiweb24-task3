## newChannel.py - a simple message channel test
##

from flask import Flask, request, render_template, jsonify
import json
import requests
from datetime import datetime, timedelta, timezone
import uuid
from better_profanity import profanity


# Class-based application configuration
class ConfigClass(object):
    """ Flask application config """

    # Flask settings
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

# Create Flask app
app = Flask(__name__, static_folder="static")
app.config.from_object(__name__ + '.ConfigClass')  # configuration
app.app_context().push()  # create an app context before initializing db

HUB_URL = 'http://localhost:5555'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "Events of Osnabrück Channel"
CHANNEL_ENDPOINT = "http://localhost:5002" # don't forget to adjust in the bottom of the file
CHANNEL_FILE = 'newmessages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'

# Message constraints
MAX_MESSAGES = 5  # Keep only the latest 100 messages
MESSAGE_EXPIRY = timedelta(days=30)  # Messages older than a day will be deleted
BANNED_WORDS = {"spam", "fuck", "scheisse"}  # Banned words list
# maybe we can use hatewords datsets


@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT

    # send a POST request to server /channels
    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                             data=json.dumps({
                                "name": CHANNEL_NAME,
                                "endpoint": CHANNEL_ENDPOINT,
                                "authkey": CHANNEL_AUTHKEY,
                                "type_of_service": CHANNEL_TYPE_OF_SERVICE,
                             }))

    if response.status_code != 200:
        print("Error creating channel: "+str(response.status_code))
        print(response.text)
        return

def check_authorization(request):
    global CHANNEL_AUTHKEY
    # check if Authorization header is present
    if 'Authorization' not in request.headers:
        return False
    # check if authorization header is valid
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name':CHANNEL_NAME}),  200

# GET: Return list of messages
@app.route('/', methods=['GET'])
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    # fetch channels from server
    return jsonify(get_active_messages()) # 원래 read_messages() 였음

# POST: Send a message
@app.route('/', methods=['POST'])
def send_message():
    # fetch channels from server
    # check authorization header
    if not check_authorization(request):
        return "Invalid authorization", 400
    # check if message is present
    message = request.json
    if not message:
        return "No message", 400
    if not 'content' in message:
        return "No content", 400
    if not 'sender' in message:
        return "No sender", 400
    if not 'timestamp' in message:
        return "No timestamp", 400
    if not 'extra' in message:
        extra = None
    else:
        extra = message['extra']

    # Get message details
    message_id = str(uuid.uuid4())
    content = message['content'].strip() # string
    sender = message['sender']  #string

    now = datetime.strftime(datetime.now(timezone.utc), '%Y-%m-%d %H:%M:%S')
    timestamp = now
    active = True


    # add message to messages
    messages = read_messages()

    messages.append({'id': message_id,
                     'content': message['content'],
                     'sender': message['sender'],
                     'timestamp': now,
                     'extra': extra,
                     'active': True
                     })

    # save updated messages
    save_messages(messages)

    return "OK", 200

# Delete the post
## if the message is deleted by the user, the active status will be False
# return : message deleted
@app.route('/messages/<message_id>', methods=['DELETE'])
def delete_message(message_id):
    print(f"Delete message request for {message_id}")
    # if not check_authorization(request):
    #     return "Invalid authorization", 400
    # messages = read_messages()
    # print(f"Before deletion: {messages}")
    #
    # for msg in messages:
    #     if msg['id'] == message_id:
    #         print(f"Message {msg['id']} deleted")
    #         messages.delete(msg)
    #         save_messages(messages)
    #         return jsonify({'message': 'Message deleted'}), 200

    # for msg in messages:
    #     if msg['id'] == message_id:
    #         msg['active'] = False
    #         save_messages(messages)
    #         return jsonify({'message': 'Message deleted'}), 200



# only active message will be displayed
def get_active_messages():
    # Retrieve only active messages
    messages = read_messages()
    check_messages(messages) # only active messages will be saved in messages
    # Keep only active messages and enforce the limit
    active_messages = [msg for msg in messages if msg.get("active", True)]
    return active_messages[-MAX_MESSAGES:]


# Read and save messages. Return messages
def read_messages():
    global CHANNEL_FILE
    try:
        f = open(CHANNEL_FILE, 'r')
    except FileNotFoundError:
        return []
    try:
        messages = json.load(f)
    except json.decoder.JSONDecodeError:
        messages = []
    f.close()
    return messages

def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)


######### Here are the filter functions #########
def is_expired(timestamp):
    """Check if a message timestamp is expired."""
    now = datetime.now(timezone.utc)
    message_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    return now - message_time > MESSAGE_EXPIRY

def profanity_check(content):
    profanity.load_censor_words()
    if profanity.contains_profanity(content):
        return True
    return False # No banned words found  

# Check messages for expiry and banned words
def check_messages(messages=None):
    """Update message status based on expiry and banned words."""
    messages = messages or read_messages()  # Load messages if not provided

    for msg in messages:
        if is_expired(msg["timestamp"]):
            print(f"Message {msg['id']} expired")
            msg["active"] = False
        elif profanity_check(msg["content"]):
            print(f"Message {msg['id']} contains a banned word")
            msg["active"] = False

    save_messages(messages)  # Save updated message statuses


# Start development web server
# run flask --app channel.py register
# to register channel with hub

if __name__ == '__main__':
    app.run(port=5002, debug=True)
