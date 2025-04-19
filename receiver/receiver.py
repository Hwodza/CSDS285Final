import eventlet
eventlet.monkey_patch()

from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO, emit
from flask_cors import CORS

app = Flask(__name__, static_url_path='', static_folder='static')
CORS(app, origins=["*"])  # For development, you can restrict this later

socketio = SocketIO(app, cors_allowed_origins="*")
data_store = {}  # Stores latest data per id

@app.route('/')
def index():
    return app.send_static_file('index.html')

@socketio.on('json_data')
def handle_json_data(data):
    if not isinstance(data, dict) or "id" not in data:
        print("Ignored packet without 'id':", data)
        return
    id_val = data["id"]
    data_store[id_val] = data
    print(f"Received and stored data for id={id_val}")
    # Emit the event with data formatted correctly
    emit('update', {str(id_val): data}, broadcast=True)  # Ensure id is a string key

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=8000, debug=True)

