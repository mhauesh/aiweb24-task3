from flask import Flask, request, render_template, jsonify
from flask_cors import CORS
import json
import requests
from datetime import datetime, timedelta, timezone
import uuid
from better_profanity import profanity

class ConfigClass(object):
    SECRET_KEY = 'This is an INSECURE secret!! DO NOT use this in production!!'

app = Flask(__name__, static_folder="static")
app.config.from_object(__name__ + '.ConfigClass')
CORS(app)
app.app_context().push()

HUB_URL = 'http://localhost:5555'
HUB_AUTHKEY = '1234567890'
CHANNEL_AUTHKEY = '0987654321'
CHANNEL_NAME = "Osnabrück Volunteers Wanted Board"
CHANNEL_ENDPOINT = "http://localhost:5002"
CHANNEL_FILE = 'newmessages.json'
CHANNEL_TYPE_OF_SERVICE = 'aiweb24:chat'
TOPIC = "Volunteer Opportunities in Osnabrück"

MAX_MESSAGES = 50  # Limit to 50 messages
MESSAGE_EXPIRY = timedelta(days=30)  # Messages expire after 30 days
WELCOME_MESSAGE = {
    "id": "welcome-0001",
    "content": "Welcome to the Osnabrück Volunteers Wanted Board! Post about volunteer opportunities or ask for help. Use [b]bold[/b] or [i]italic[/i] for emphasis. Tag your message with 'extra' like 'urgent' or 'event'.",
    "sender": "System",
    "timestamp": "2025-02-24 00:00:00",
    "extra": "pinned",
    "active": True,
    "body": None
}

@app.cli.command('register')
def register_command():
    global CHANNEL_AUTHKEY, CHANNEL_NAME, CHANNEL_ENDPOINT
    response = requests.post(HUB_URL + '/channels', headers={'Authorization': 'authkey ' + HUB_AUTHKEY},
                             data=json.dumps({
                                 "name": CHANNEL_NAME,
                                 "endpoint": CHANNEL_ENDPOINT,
                                 "authkey": CHANNEL_AUTHKEY,
                                 "type_of_service": CHANNEL_TYPE_OF_SERVICE,
                             }))
    if response.status_code != 200:
        print("Error creating channel: " + str(response.status_code))
        print(response.text)

def check_authorization(request):
    global CHANNEL_AUTHKEY
    if 'Authorization' not in request.headers:
        return False
    if request.headers['Authorization'] != 'authkey ' + CHANNEL_AUTHKEY:
        return False
    return True

@app.route('/health', methods=['GET'])
def health_check():
    global CHANNEL_NAME
    if not check_authorization(request):
        return "Invalid authorization", 400
    return jsonify({'name': CHANNEL_NAME}), 200

@app.route('/', methods=['GET'])
def home_page():
    if not check_authorization(request):
        return "Invalid authorization", 400
    messages = get_active_messages()
    # Ensure welcome message is always first
    if not any(msg["id"] == WELCOME_MESSAGE["id"] for msg in messages):
        messages.insert(0, WELCOME_MESSAGE)
    else:
        # Move pinned message to the top if it exists
        pinned = next((msg for msg in messages if msg["id"] == WELCOME_MESSAGE["id"]), None)
        if pinned:
            messages.remove(pinned)
            messages.insert(0, pinned)
    return jsonify(messages)

@app.route('/', methods=['POST'])
def send_message():
    if not check_authorization(request):
        return "Invalid authorization", 400
    message = request.json
    if not message:
        return "No message", 400
    if not 'content' in message:
        return "No content", 400
    if not 'sender' in message:
        return "No sender", 400
    if not 'timestamp' in message:
        return "No timestamp", 400
    extra = message.get('extra')
    body = message.get('body')

    content = message['content'].strip()
    sender = message['sender']
    now = datetime.strftime(datetime.now(timezone.utc), '%Y-%m-%d %H:%M:%S')
    message_id = str(uuid.uuid4())

    if profanity_check(content):
        return "No profanity allowed", 400

    messages = read_messages()
    if not any(msg["id"] == WELCOME_MESSAGE["id"] for msg in messages):
        messages.insert(0, WELCOME_MESSAGE)

    new_message = {
        'id': message_id,
        'content': content,
        'sender': sender,
        'timestamp': now,
        'extra': extra,
        'active': True,
        'body': body
    }
    messages.append(new_message)

    response_message = generate_response(content, sender, extra)
    if response_message:
        messages.append(response_message)

    save_messages(messages)
    return "OK", 200

def get_active_messages():
    messages = read_messages()
    check_messages(messages)
    active_messages = [msg for msg in messages if msg.get("active", True)]
    # Sort by timestamp, but pinned message will be adjusted in home_page
    active_messages.sort(key=lambda x: x['timestamp'], reverse=True)
    return active_messages[-MAX_MESSAGES:]

def read_messages():
    global CHANNEL_FILE
    try:
        with open(CHANNEL_FILE, 'r') as f:
            messages = json.load(f)
    except (FileNotFoundError, json.decoder.JSONDecodeError):
        messages = [WELCOME_MESSAGE]
    return messages

def save_messages(messages):
    global CHANNEL_FILE
    with open(CHANNEL_FILE, 'w') as f:
        json.dump(messages, f)

def is_expired(timestamp):
    now = datetime.now(timezone.utc)
    message_time = datetime.strptime(timestamp, '%Y-%m-%d %H:%M:%S').replace(tzinfo=timezone.utc)
    return now - message_time > MESSAGE_EXPIRY

def profanity_check(content):
    profanity.load_censor_words()
    custom_banned = ["spam", "hate", "jerk"]
    return profanity.contains_profanity(content) or any(word in content.lower() for word in custom_banned)

def check_messages(messages=None):
    messages = messages or read_messages()
    for msg in messages:
        if msg["id"] == WELCOME_MESSAGE["id"]:  # Welcome message never expires
            continue
        if is_expired(msg["timestamp"]):
            print(f"Message {msg['id']} expired")
            msg["active"] = False
        elif profanity_check(msg["content"]):
            print(f"Message {msg['id']} contains a banned word")
            msg["active"] = False
    save_messages(messages)

def generate_response(content, sender, extra):
    now = datetime.strftime(datetime.now(timezone.utc), '%Y-%m-%d %H:%M:%S')
    content_lower = content.lower()

    if "looking for volunteers" in content_lower:
        return {
            "id": str(uuid.uuid4()),
            "content": f"@{sender}, thanks for posting! Please provide more details (e.g., date, location) so others can join.",
            "sender": "VolunteerBot",
            "timestamp": now,
            "extra": "auto-response",
            "active": True,
            "body": None
        }
    elif "can help" in content_lower or "available" in content_lower:
        return {
            "id": str(uuid.uuid4()),
            "content": f"@{sender}, great to hear! Please connect with recent posters or check pinned messages for opportunities.",
            "sender": "VolunteerBot",
            "timestamp": now,
            "extra": "auto-response",
            "active": True,
            "body": None
        }
    elif "event" in str(extra).lower():
        return {
            "id": str(uuid.uuid4()),
            "content": f"@{sender}, your event has been noted! Consider adding it to the Osnabrück Volunteer Calendar (ask VolunteerBot for details).",
            "sender": "VolunteerBot",
            "timestamp": now,
            "extra": "event-notice",
            "active": True,
            "body": None
        }
    return None

if __name__ == '__main__':
    app.run(port=5002, debug=True)