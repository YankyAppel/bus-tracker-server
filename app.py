from flask import Flask, request
from flask_cors import CORS
import logging
import sys
import json

# =============================================================================
# EXTREMELY EXPLICIT LOGGING SETUP
# This is a last-ditch effort to force logs to appear on Heroku.
# =============================================================================
app = Flask(__name__)

# Configure a handler to write to standard output, which Heroku captures
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# Also add a basic config as a backup
logging.basicConfig(level=logging.INFO)

# Enable CORS
CORS(app)

app.logger.info("SERVER CODE STARTED: Logging has been configured.")
print("SERVER CODE STARTED: This is a print statement.", file=sys.stdout)


# This is our simple in-memory "database"
bus_locations = {}


# =============================================================================
# SERVER ROUTES
# =============================================================================

# Main page to check if the server is alive
@app.route('/')
def index():
    app.logger.info("ROOT_URL_ACCESS: '/' was hit.")
    print("ROOT_URL_ACCESS: '/' was hit via print.", file=sys.stdout)
    return "Hello, World! The GPS server is running with SUPER LOGGING."

# Endpoint where the driver's app will send location data
@app.route('/location', methods=['POST'])
def receive_location():
    app.logger.info("LOCATION_ENDPOINT_HIT: Received a POST request to /location.")
    print("LOCATION_ENDPOINT_HIT: Received a POST request to /location.", file=sys.stdout)
    
    try:
        data = request.get_json()
        if not data:
            app.logger.error("BAD_REQUEST_ERROR: Request body is not JSON or is empty.")
            print("BAD_REQUEST_ERROR: Request body is not JSON or is empty.", file=sys.stdout)
            return "Bad Request: No JSON data received.", 400

        bus_id = data.get('bus_id')
        lat = data.get('lat')
        lon = data.get('lon')

        if not all([bus_id, lat, lon]):
            app.logger.error(f"BAD_REQUEST_ERROR: Incomplete data. Received: {data}")
            print(f"BAD_REQUEST_ERROR: Incomplete data. Received: {data}", file=sys.stdout)
            return "Bad Request: Incomplete data provided.", 400

        # Store the latest location
        bus_locations[bus_id] = {'lat': lat, 'lon': lon}

        # Log the received data so we can see it in Heroku logs
        app.logger.info(f"SUCCESS: Received location for Bus {bus_id}: Lat={lat}, Lon={lon}")
        print(f"SUCCESS: Received location for Bus {bus_id}: Lat={lat}, Lon={lon}", file=sys.stdout)
        
        return "Location received", 200

    except Exception as e:
        app.logger.critical(f"CRITICAL_SERVER_ERROR: An unexpected error occurred: {e}")
        print(f"CRITICAL_SERVER_ERROR: An unexpected error occurred: {e}", file=sys.stdout)
        return "Internal Server Error", 500

