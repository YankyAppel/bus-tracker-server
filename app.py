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
    "https://chimerical-salamander-bf8231.netlify.app", # Admin App
    "null"
])

app.logger.info("SERVER CODE STARTED - Bus List Endpoints Active")

# --- In-memory "database" ---
bus_locations = {}
bus_list = [] # NEW: To store the list of bus names

# --- Server Routes ---

@app.route('/')
def index():
    return "Hello, World! The Bus Tracker server is running."

# --- Bus List Management (for Admin Page) ---

@app.route('/buses', methods=['GET'])
def get_buses():
    app.logger.info(f"GET_BUSES_SUCCESS: Sent bus list: {bus_list}")
    return jsonify(bus_list)

@app.route('/buses', methods=['POST'])
def add_bus():
    data = request.get_json()
    if not data or 'name' not in data:
        return jsonify({"error": "Bus name is required"}), 400
    
    bus_name = data['name']
    if bus_name not in bus_list:
        bus_list.append(bus_name)
        app.logger.info(f"ADD_BUS_SUCCESS: Added '{bus_name}'. Current list: {bus_list}")
    else:
        app.logger.info(f"ADD_BUS_FAIL: '{bus_name}' already exists.")
        
    return jsonify({"message": f"Bus '{bus_name}' processed.", "buses": bus_list}), 200

# --- Routes for Bus Location Tracking ---

@app.route('/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    if not data or not all(k in data for k in ['bus_id', 'lat', 'lon']):
        return "Bad Request: Incomplete data provided.", 400

    bus_id = data['bus_id']
    lat = data.get('lat')
    lon = data.get('lon')

    bus_locations[bus_id] = {'lat': lat, 'lon': lon}
    app.logger.info(f"SUCCESS: Received location for Bus {bus_id}: Lat={lat}, Lon={lon}")
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

