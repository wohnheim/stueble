from flask import request, Flask
from flask_socketio import SocketIO, emit, join_room, leave_room

app = Flask(__name__)
socketio = SocketIO(app, cors_allowed_origins="*")

@socketio.on('connect')
def handle_connect():
    print("SID in connect:", request.sid)
    emit('connected', request.sid)

if __name__ == '__main__':
    socketio.run(app)