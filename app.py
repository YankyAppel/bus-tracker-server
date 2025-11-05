from flask import Flask, request
from flask_cors import CORS
import logging
import json

# 1. Setup
app = Flask(__name__)
CORS(app) # Enable Cross-Origin Resource Sharing

# Set up basic logging to see output in Heroku logs
logging.basicConfig(level=logging.INFO)

# This is our simple in-memory "database"
# It will store the latest location for each bus ID
bus_locations = {}


# 2. Server Routes

# This is the main page, to check if the server is alive
@app.route('/')
def index():
    app.logger.info("Root URL '/' was accessed. Server is running.")
    return "Hello, World! The GPS server is running."

# This is the endpoint where the driver's app will send location data
@app.route('/location', methods=['POST'])
def receive_location():
    try:
        data = request.get_json()
        bus_id = data.get('bus_id')
        lat = data.get('lat')
        lon = data.get('lon')

        if not all([bus_id, lat, lon]):
            app.logger.warning(f"Incomplete data received: {data}")
            return "Incomplete data", 400

        # Store the latest location
        bus_locations[bus_id] = {'lat': lat, 'lon': lon}

        # Log the received data so we can see it in Heroku logs
        app.logger.info(f"Received location for Bus {bus_id}: Lat={lat}, Lon={lon}")

        # Also print the entire database for debugging
        app.logger.info(f"Current bus locations: {json.dumps(bus_locations)}")

        return "Location received", 200

    except Exception as e:
        app.logger.error(f"Error processing location request: {e}")
        return "Server error", 500

# This is the endpoint the parent's SMS will use
@app.route('/bus_location', methods=['GET'])
def get_bus_location():
    # This part is not fully built out yet, but we'll add it later.
    # For now, it just returns all known data.
    return jsonify(bus_locations)


