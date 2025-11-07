from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sys

app = Flask(__name__)

# --- Logging Setup ---
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# --- CORS SETUP ---
CORS(app, origins=[
    "https://gleaming-brigadeiros-6bbd55.netlify.app",  # Parent App
    "https://darling-ganache-26a871.netlify.app",       # Driver App
    "null", # Allow local file testing
    # We will add the Admin App URL here once it's created
])

app.logger.info("SERVER CODE STARTED")

# --- In-memory "database" ---
bus_locations = {}
bus_list = [] # NEW: To store the list of bus names


# --- Server Routes ---

@app.route('/')
def index():
    return "Hello, World! The GPS server is running."

# --- Routes for Bus Location Tracking ---

@app.route('/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    if not data or not all(k in data for k in ['bus_id', 'lat', 'lon']):
        return "Bad Request: Incomplete data provided.", 400
    
    bus_id = data['bus_id']
    bus_locations[bus_id] = {'lat': data['lat'], 'lon': data['lon']}
    app.logger.info(f"SUCCESS: Received location for Bus {bus_id}")
    return "Location received", 200

@app.route('/get_location', methods=['GET'])
def get_location():
    bus_id = request.args.get('bus_id')
    if not bus_id:
        return jsonify({"error": "Please provide a bus_id parameter."}), 400

    location = bus_locations.get(bus_id)
    if location:
        return jsonify(location)
    else:
        return jsonify({"error": f"No location found for bus {bus_id}."}), 404


# --- NEW: Routes for Managing the Bus List ---

@app.route('/buses', methods=['GET'])
def get_buses():
    app.logger.info(f"GET_BUS_LIST: Sent bus list: {bus_list}")
    return jsonify(bus_list)

@app.route('/buses', methods=['POST'])
def add_bus():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Bus name not provided."}), 400
    
    bus_name = data['name']
    if bus_name not in bus_list:
        bus_list.append(bus_name)
        app.logger.info(f"ADD_BUS: Added '{bus_name}' to the list. Current list: {bus_list}")
        return jsonify({"message": f"Bus '{bus_name}' added.", "buses": bus_list}), 201
    else:
        return jsonify({"message": "Bus already exists."}), 200

