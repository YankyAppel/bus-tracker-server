from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sys
import os
import psycopg2
from psycopg2 import pool

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

# --- Database Connection (Robust version) ---
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    app.logger.critical("FATAL: DATABASE_URL environment variable not set.")
    sys.exit("FATAL: DATABASE_URL not found.")

try:
    app.db_pool = psycopg2.pool.SimpleConnectionPool(1, 5, dsn=db_url)
    app.logger.info("Database connection pool created successfully.")
except Exception as e:
    app.logger.critical(f"FATAL: Failed to create database connection pool: {e}")
    sys.exit("FATAL: Database connection failed.")


# In-memory store for bus locations (still useful for real-time speed)
bus_locations = {}

@app.route('/')
def index():
    return "Hello, World! The GPS server with DB connection is running."


# --- Location Endpoints (Real-time, no DB needed for this part) ---

@app.route('/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    bus_id = data.get('bus_id')
    lat = data.get('lat')
    lon = data.get('lon')

    if not all([bus_id, lat, lon]):
        return "Bad Request: Incomplete data provided.", 400

    bus_locations[bus_id] = {'lat': lat, 'lon': lon}
    app.logger.info(f"Received location for Bus {bus_id}: Lat={lat}, Lon={lon}")
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


# --- Bus Management Endpoints (Now connected to DB) ---

@app.route('/buses', methods=['GET', 'POST'])
def manage_buses():
    conn = app.db_pool.getconn()
    try:
        with conn.cursor() as cur:
            if request.method == 'POST':
                data = request.get_json()
                bus_name = data.get('name')
                if not bus_name:
                    return jsonify({"error": "Bus name is required"}), 400
                
                cur.execute("INSERT INTO buses (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;", (bus_name,))
                conn.commit()
                app.logger.info(f"Added or found bus: {bus_name}")

            cur.execute("SELECT name FROM buses ORDER BY name;")
            buses = [row[0] for row in cur.fetchall()]
            return jsonify(buses)

    except Exception as e:
        conn.rollback()
        app.logger.error(f"Database error in /buses: {e}")
        return jsonify({"error": "A database error occurred."}), 500
    finally:
        if conn:
            app.db_pool.putconn(conn)

