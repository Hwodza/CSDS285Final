from flask import Flask, request, jsonify, render_template_string

app = Flask(__name__)
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
    return render_template_string('''
        <html>
        <head><title>Received JSON Data</title></head>
        <body>
            <h1>Received JSON Data</h1>
            <pre>{{ data | tojson(indent=2) }}</pre>
        </body>
        </html>
    ''', data=received_data)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)

