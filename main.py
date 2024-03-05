from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_socketio import join_room, leave_room, send, SocketIO
import random
from string import ascii_uppercase
import speech_recognition as sr
from googletrans import Translator
from engineio.async_drivers import gevent
import json, io
from gtts import gTTS
import base64
from flask_cors import CORS
from datetime import datetime

app = Flask(__name__)
CORS(app)
translator = Translator()
app.config["SECRET_KEY"] = "192b9bdd22ab9ed4d12e236c78afcb9a393ec15f71bbf5dc987d54727823bcbf"
socketio = SocketIO(app, cors_allowed_origins="*")

ngrok_url = "https://52bf-122-161-185-176.ngrok-free.app"

def get_audio_data(text, language='en'):
    myobj = gTTS(text=text, lang=language, slow=False)
    mp3_fp = io.BytesIO()
    myobj.write_to_fp(mp3_fp)
    mp3_fp.seek(0)
    return base64.b64encode(mp3_fp.read()).decode('utf-8')

@app.after_request
def add_header(response):
    response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
    return response

rooms = {}
users = []
rooms_data = {}

def generate_unique_code(length):
    while True:
        code = ""
        for _ in range(length):
            code += random.choice(ascii_uppercase)

        if code not in rooms:
            break
    return code

@app.route("/", methods=["POST", "GET"])
def home():
    print(rooms_data)
    print('baseurl')
    print(session)
    session.clear()
    print(session)
    if request.method == "POST":
        name = request.form.get("name")
        code = request.form.get("code")
        join = request.form.get("join", False)
        create = request.form.get("create", False)

        if not name:
            return render_template("home.html", error="Please enter a name.", code=code, name=name)

        if join != False and not code:
            return render_template("home.html", error="Please enter a room code.", code=code, name=name)

        room = code
        if create != False:
            room = generate_unique_code(4)
            rooms[room] = {"members": 0, "messages": [], "users": []}
        elif code not in rooms:
            return render_template("home.html", error="Room does not exist.", code=code, name=name)

        session["room"] = room
        session["name"] = name
        print(session)
        print("move from home")
        return redirect(url_for("room"))

    return render_template("home.html")

@app.route("/room")
def room():
    print("enter room")
    room = session.get("room")
    if room is None or session.get("name") is None or room not in rooms:
        return redirect(url_for("home"))
    print(session)
    return render_template("room.html", code=room, messages=rooms[room]["messages"])

@socketio.on("play_audio")
def play_audio(data):
    language_code = data.get('languageCode')
    message_text = data.get('messageText')

    try:
        # Call the play_text_as_audio function with the provided parameters
        audio_data = get_audio_data(message_text, language_code)

        # Emit the audio data only to the user who triggered the event
        socketio.emit("play_audio", {'audioData': audio_data}, room=request.sid)
    except Exception as e:
        print(f"Error: {e}")


def translate_message(message, source_language, target_language):
    try:
        translation = translator.translate(message, src=source_language, dest=target_language)
        print(translation)
        return translation.text
    except Exception as e:
        print(f"Translation error: {e}")
        return message

def detect_language(text):
    result = translator.detect(text)
    return result.lang

@socketio.on("message")
def message(data):
    print(data)
    room = session.get("room")
    if room not in rooms:
        return

    sender_socket_id = request.sid
    sender_user = next((u for u in rooms[room]["users"] if u["socket_id"] == sender_socket_id), None)
    if not sender_user:
        return

    sender_name = sender_user["name"]
    message_content = data["data"]
    language = detect_language(message_content)
    print("language : ", language)
    current_datetime = datetime.now()
    date = current_datetime.strftime("%d,%b %Y %I:%M %p")

    if room not in rooms_data:
        rooms_data[room] = {}

    for item in rooms[room]["users"]:
        if item['name'] not in rooms_data[room]:
            rooms_data[room][item['name']] = []

    for recipient_user in rooms[room]["users"]:
        if recipient_user["socket_id"] != sender_socket_id:
            target_language = recipient_user["language"]
            translated_message = translate_message(message_content, sender_user["language"], target_language)

            content = {
                "name": sender_name,
                "message": translated_message,
                "language": target_language,
                "date": date
            }

            socketio.emit("play_audio", {'audioData': translated_message})  # Adjust as needed

            send(content, to=recipient_user["socket_id"])
            print(recipient_user)
            receiver_name = recipient_user.get('name')
            rooms_data[room][receiver_name].append(content)
            print(rooms_data)
            print(rooms_data[room][sender_name])
            print(f"{sender_name} said: {message_content} (translated to {language})")
            print(f"{sender_name} said: {translated_message} (translated to {target_language})")

    content = {
        "name": sender_name,
        "message": message_content,
        "language": language,
        "date": date
    }
    rooms_data[room][sender_name].append(content)
    send(content)
    print(rooms_data)
    print(rooms_data[room][sender_name])
    print(f"{sender_name} said: {message_content}")

@socketio.on("connect")
def connect(auth):
    print('connecting')
    room = session.get("room")
    name = session.get("name")
    if not room or not name:
        return
    if room not in rooms:
        leave_room(room)
        return

    if room in rooms_data and name in rooms_data[room]:
        stored_data = rooms_data[room][name]
        for content in stored_data:
            send(content, to=request.sid)

    join_room(room)
    current_datetime = datetime.now()
    date = current_datetime.strftime("%d,%b %Y %I:%M %p")
    send({"name": name, "message": "has entered the room", "language": "en", "date": date}, to=room)

    user_data = {"socket_id": request.sid, "name": name, "language": "en"}
    rooms[room]["users"].append(user_data)

    rooms[room]["members"] += 1
    print(f"{name} joined room {room}")
    print("Current users connected:", rooms[room]["users"])

@socketio.on("disconnect")
def disconnect():
    try:
        room = session.get("room")
        name = session.get("name")

        if room in rooms and "users" in rooms[room]:
            leave_room(room)
            rooms[room]["members"] -= 1

            if rooms[room]["members"] <= 0:
                if room in rooms_data:
                    del rooms_data[room]
                del rooms[room]

            rooms[room]["users"] = [user for user in rooms[room]["users"] if user["socket_id"] != request.sid]

            current_datetime = datetime.now()
            date = current_datetime.strftime("%d,%b %Y %I:%M %p")
            send({"name": name, "message": "has left the room", "language": "en", "date": date}, to=room)
            print(f"{name} has left the room {room}")
            print("Current users deleted:", rooms[room]["users"])

    except Exception as e:
        print(f"Disconnect handler error: {e}. Ignoring disconnection.")

@socketio.on("changeLanguage")
def LanguageChange(data):
    print("Language changed")
    print(data)
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except json.JSONDecodeError:
            print("Invalid JSON format for changeLanguage event.")
            return
        
    new_language = data.get('language')
    print("rooms",rooms)
    print("rooms_data", rooms_data)

    room = session.get("room")
    
    if room is None:
        print("Room not found in session.")
        return

    user = next((u for u in rooms[room]["users"] if u["socket_id"] == request.sid), None)
    print("user",user)
    if user:
        # user["language"] = new_language
        # rooms[room]["users"]["language"] = new_language
        rooms[room]["users"][rooms[room]["users"].index(user)]["language"] = new_language
        print(f"User {user['name']} changed language to {new_language}")

    print("Current rooms:", rooms)


if __name__ == "__main__":
    socketio.run(app, debug=True, port=7500, host='0.0.0.0') 
