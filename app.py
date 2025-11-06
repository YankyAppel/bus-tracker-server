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
# Allow requests from BOTH of your Netlify domains
CORS(app, origins=[
    "https://gleaming-brigadeiros-6bbd55.netlify.app", # Parent App
    "https://darling-ganache-26a871.netlify.app"      # Driver App
])

app.logger.info("SERVER CODE STARTED with CORS for BOTH Netlify apps")

# This is our simple in-memory "database"
bus_locations = {}

# --- Server Routes ---

@app.route('/')
def index():
    app.logger.info("ROOT_URL_ACCESS: '/' was hit.")
    return "Hello, World! The GPS server is running."

@app.route('/location', methods=['POST'])
def receive_location():
    app.logger.info("LOCATION_ENDPOINT_HIT: Received a POST request to /location.")
    try:
        data = request.get_json()
        if not data:
            app.logger.error("BAD_REQUEST_ERROR: Request body is not JSON or is empty.")
            return "Bad Request: No JSON data received.", 400

        bus_id = data.get('bus_id')
        lat = data.get('lat')
        lon = data.get('lon')

        if not all([bus_id, lat, lon]):
            app.logger.error(f"BAD_REQUEST_ERROR: Incomplete data. Received: {data}")
            return "Bad Request: Incomplete data provided.", 400

        bus_locations[bus_id] = {'lat': lat, 'lon': lon}
        app.logger.info(f"SUCCESS: Received location for Bus {bus_id}: Lat={lat}, Lon={lon}")
        return "Location received", 200

    except Exception as e:
        app.logger.critical(f"CRITICAL_SERVER_ERROR: An unexpected error occurred: {e}")
        return "Internal Server Error", 500

# --- ROUTE FOR PARENTS ---
@app.route('/get_location', methods=['GET'])
def get_location():
    bus_id = request.args.get('bus_id')
    if not bus_id:
        app.logger.warning("GET_LOCATION_FAIL: Request missing bus_id.")
        return jsonify({"error": "Please provide a bus_id parameter."}), 400

    location = bus_locations.get(bus_id)
    if location:
        app.logger.info(f"GET_LOCATION_SUCCESS: Sent location for {bus_id}.")
        return jsonify(location)
    else:
        app.logger.warning(f"GET_LOCATION_FAIL: No location found for {bus_id}.")
        return jsonify({"error": f"No location found for bus {bus_id}."}), 404

