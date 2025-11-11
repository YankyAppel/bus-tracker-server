# Base Imports
from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sys
import os

# Database Imports
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

# --- Database Connection Pool ---
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    app.logger.critical("FATAL: DATABASE_URL environment variable not set.")
    sys.exit("FATAL: DATABASE_URL not found.")

try:
    app.db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=db_url)
    app.logger.info("Database connection pool created successfully.")
except Exception as e:
    app.logger.critical(f"FATAL: Failed to create database connection pool: {e}")
    sys.exit("FATAL: Database connection failed.")

# In-memory store for bus locations (for real-time speed)
bus_locations = {}

@app.route('/')
def index():
    return "Hello, World! The GPS server with DB and Route Management is running."

# --- Location Endpoints ---
@app.route('/location', methods=['POST'])
def receive_location():
    data = request.get_json()
    bus_id = data.get('bus_id')
    lat = data.get('lat')
    lon = data.get('lon')
    if not all([bus_id, lat, lon]):
        return "Bad Request: Incomplete data provided.", 400
    bus_locations[bus_id] = {'lat': lat, 'lon': lon}
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

# --- Bus Management Endpoints ---
@app.route('/buses', methods=['GET', 'POST'])
def manage_buses():
    conn = None
    try:
        conn = app.db_pool.getconn()
        with conn.cursor() as cur:
            if request.method == 'POST':
                data = request.get_json()
                bus_name = data.get('name')
                if not bus_name:
                    return jsonify({"error": "Bus name is required"}), 400
                cur.execute("INSERT INTO buses (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;", (bus_name,))
                conn.commit()
            cur.execute("SELECT id, name FROM buses ORDER BY name;")
            buses = [{'id': row[0], 'name': row[1]} for row in cur.fetchall()]
            return jsonify(buses)
    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Database error in /buses: {e}")
        return jsonify({"error": "A database error occurred."}), 500
    finally:
        if conn:
            app.db_pool.putconn(conn)

# --- NEW: Route Management Endpoints ---

@app.route('/routes', methods=['GET', 'POST'])
def manage_routes():
    conn = None
    try:
        conn = app.db_pool.getconn()
        with conn.cursor() as cur:
            if request.method == 'POST':
                data = request.get_json()
                route_name = data.get('name')
                if not route_name:
                    return jsonify({"error": "Route name is required"}), 400
                
                cur.execute("INSERT INTO routes (name) VALUES (%s) RETURNING id, name;", (route_name,))
                conn.commit()
                new_route = cur.fetchone()
                return jsonify({'id': new_route[0], 'name': new_route[1], 'stops': []}), 201

            # On GET request, fetch all routes and their stops
            cur.execute("SELECT id, name FROM routes ORDER BY name;")
            routes = cur.fetchall()
            
            routes_with_stops = []
            for route_row in routes:
                route_id = route_row[0]
                route_name = route_row[1]
                
                cur.execute("SELECT address, sequence FROM stops WHERE route_id = %s ORDER BY sequence;", (route_id,))
                stops_data = cur.fetchall()
                stops = [{'address': stop[0], 'sequence': stop[1]} for stop in stops_data]
                
                routes_with_stops.append({
                    'id': route_id,
                    'name': route_name,
                    'stops': stops
                })
            
            return jsonify(routes_with_stops)

    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Database error in /routes: {e}")
        return jsonify({"error": "A database error occurred."}), 500
    finally:
        if conn:
            app.db_pool.putconn(conn)


@app.route('/routes/<int:route_id>/stops', methods=['POST'])
def add_stop_to_route(route_id):
    conn = None
    try:
        conn = app.db_pool.getconn()
        data = request.get_json()
        address = data.get('address')
        if not address:
            return jsonify({"error": "Address is required"}), 400

        with conn.cursor() as cur:
            # Get the next sequence number for this route
            cur.execute("SELECT COALESCE(MAX(sequence), 0) + 1 FROM stops WHERE route_id = %s;", (route_id,))
            next_sequence = cur.fetchone()[0]

            cur.execute("INSERT INTO stops (route_id, address, sequence) VALUES (%s, %s, %s);", (route_id, address, next_sequence))
            conn.commit()
            return jsonify({"success": True, "message": f"Stop added to route {route_id}"}), 201

    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Database error in /routes/stops: {e}")
        return jsonify({"error": "A database error occurred."}), 500
    finally:
        if conn:
            app.db_pool.putconn(conn)

