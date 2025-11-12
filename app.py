import os
from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
from psycopg2 import pool
import bleach

app = Flask(__name__)

# Setup connection pool
try:
    app.db_pool = psycopg2.pool.SimpleConnectionPool(
        1, 10, dsn=os.environ.get("DATABASE_URL")
    )
    app.logger.info("Database connection pool created successfully.")
except Exception as e:
    app.logger.error(f"Failed to create database connection pool: {e}")
    app.db_pool = None

# Define allowed origins
# Be sure to replace placeholders with your actual Netlify URLs
CORS(app, origins=[
    "https://gleaming-brigadeiros-6bbd55.netlify.app",  # Parent App
    "https://darling-ganache-26a871.netlify.app",      # Original Admin App
    "https://chimerical-salamander-bf8231.netlify.app", # New Admin App
    "https://darling-ganache-26a871.netlify.app",         # Driver app URL
    "null"
])

@app.route('/')
def index():
    return "Bus Tracker Server is running!"

def get_db_connection():
    if not app.db_pool:
        raise Exception("Database pool is not initialized.")
    return app.db_pool.getconn()

def release_db_connection(conn):
    if app.db_pool and conn:
        app.db_pool.putconn(conn)

@app.route('/buses', methods=['POST'])
def add_bus():
    conn = None
    try:
        conn = get_db_connection()
        data = request.get_json()
        bus_name = bleach.clean(data.get('bus_name'))
        if not bus_name:
            return jsonify({"error": "Bus name is required"}), 400
        with conn.cursor() as cur:
            cur.execute("INSERT INTO buses (name) VALUES (%s) RETURNING id, name;", (bus_name,))
            new_bus = cur.fetchone()
            conn.commit()
            return jsonify({"id": new_bus[0], "name": new_bus[1]}), 201
    except Exception as e:
        app.logger.error(f"Error adding bus: {e}")
        return jsonify({"error": "Failed to add bus."}), 500
    finally:
        release_db_connection(conn)

@app.route('/buses', methods=['GET'])
def get_buses():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM buses ORDER BY name;")
            buses = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
            return jsonify(buses)
    except Exception as e:
        app.logger.error(f"Error getting buses: {e}")
        return jsonify({"error": "Failed to retrieve buses."}), 500
    finally:
        release_db_connection(conn)

@app.route('/update_location', methods=['POST'])
def update_location():
    conn = None
    try:
        conn = get_db_connection()
        data = request.get_json()
        bus_id = bleach.clean(data.get('bus_id'))
        lat = data.get('lat')
        lng = data.get('lng')
        if not all([bus_id, lat, lng]):
            return jsonify({"error": "Missing bus_id, lat, or lng"}), 400
        with conn.cursor() as cur:
            # Update location and return the new timestamp
            cur.execute(
                "UPDATE locations SET lat = %s, lng = %s, timestamp = NOW() WHERE bus_id = %s RETURNING timestamp;",
                (lat, lng, bus_id)
            )
            # If no row was updated, it means the bus_id doesn't exist in locations table yet.
            if cur.rowcount == 0:
                cur.execute(
                    "INSERT INTO locations (bus_id, lat, lng) VALUES (%s, %s, %s) RETURNING timestamp;",
                    (bus_id, lat, lng)
                )
            timestamp = cur.fetchone()[0]
            conn.commit()
            app.logger.info(f"SUCCESS: Received location for Bus {bus_id}")
            return jsonify({"message": "Location updated successfully", "timestamp": timestamp}), 200
    except Exception as e:
        app.logger.error(f"Error updating location: {e}")
        return jsonify({"error": "Failed to update location."}), 500
    finally:
        release_db_connection(conn)

@app.route('/get_location', methods=['GET'])
def get_location():
    conn = None
    try:
        conn = get_db_connection()
        bus_id = bleach.clean(request.args.get('bus_id'))
        if not bus_id:
            return jsonify({"error": "bus_id parameter is required"}), 400
        with conn.cursor() as cur:
            cur.execute(
                "SELECT lat, lng, timestamp FROM locations WHERE bus_id = %s;", (bus_id,)
            )
            location = cur.fetchone()
            if location:
                return jsonify({"lat": location[0], "lng": location[1], "timestamp": location[2].isoformat()})
            else:
                return jsonify({"error": "Location not found for this bus"}), 404
    except Exception as e:
        app.logger.error(f"Error getting location: {e}")
        return jsonify({"error": "Failed to retrieve location."}), 500
    finally:
        release_db_connection(conn)

@app.route('/routes', methods=['POST'])
def create_route():
    conn = None
    try:
        conn = get_db_connection()
        data = request.get_json()
        route_name = bleach.clean(data.get('name'))
        if not route_name:
            return jsonify({"error": "Route name is required"}), 400
        with conn.cursor() as cur:
            cur.execute("INSERT INTO routes (name) VALUES (%s) RETURNING id, name;", (route_name,))
            new_route = cur.fetchone()
            conn.commit()
            app.logger.info(f"Created route '{new_route[1]}' with ID {new_route[0]}")
            return jsonify({"id": new_route[0], "name": new_route[1]}), 201
    except Exception as e:
        app.logger.error(f"Error creating route: {e}")
        return jsonify({"error": "Failed to create route"}), 500
    finally:
        release_db_connection(conn)

@app.route('/routes', methods=['GET'])
def get_routes():
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT id, name FROM routes ORDER BY name;")
            routes = [{"id": row[0], "name": row[1]} for row in cur.fetchall()]
            return jsonify(routes)
    except Exception as e:
        app.logger.error(f"Error getting routes: {e}")
        return jsonify({"error": "Failed to retrieve routes."}), 500
    finally:
        release_db_connection(conn)

@app.route('/routes/<int:route_id>/stops', methods=['POST'])
def add_stop_to_route(route_id):
    conn = None
    try:
        conn = get_db_connection()
        data = request.get_json()
        address = bleach.clean(data.get('address'))
        sequence = data.get('sequence')
        if not address or sequence is None:
            return jsonify({"error": "Address and sequence are required"}), 400
        with conn.cursor() as cur:
            cur.execute(
                "INSERT INTO stops (route_id, address, sequence) VALUES (%s, %s, %s) RETURNING id;",
                (route_id, address, sequence)
            )
            stop_id = cur.fetchone()[0]
            conn.commit()
            app.logger.info(f"Added stop '{address}' to route {route_id} at sequence {sequence}")
            return jsonify({"id": stop_id}), 201
    except Exception as e:
        app.logger.error(f"Error adding stop: {e}")
        return jsonify({"error": "Failed to add stop"}), 500
    finally:
        release_db_connection(conn)

@app.route('/routes/<int:route_id>/stops', methods=['GET'])
def get_stops_for_route(route_id):
    conn = None
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, address, sequence FROM stops WHERE route_id = %s ORDER BY sequence;",
                (route_id,)
            )
            stops = [{"id": row[0], "address": row[1], "sequence": row[2]} for row in cur.fetchall()]
            return jsonify(stops)
    except Exception as e:
        app.logger.error(f"Error getting stops: {e}")
        return jsonify({"error": "Failed to retrieve stops."}), 500
    finally:
        release_db_connection(conn)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

