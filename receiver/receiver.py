from flask import Flask, request, jsonify
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
CORS(app, origins=["http://eecslab-22.case.edu"])  # Only allow this origin

# CORS(app)  # Enable CORS for the entire app

received_data = []  # Store received JSON objects

@app.route('/data', methods=['POST'])
def receive_data():
    global received_data
    data = request.get_json()
    if data:
        received_data.append(data)
        return jsonify({"message": "Data received successfully", "data": data}), 200
    return jsonify({"error": "Invalid JSON"}), 400

@app.route('/')
def display_data():
    return jsonify(received_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

