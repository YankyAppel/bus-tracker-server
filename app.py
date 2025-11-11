from flask import Flask, request, jsonify
from flask_cors import CORS
import logging
import sys
import os
import psycopg2
from psycopg2 import pool
from psycopg2.extras import DictCursor

app = Flask(__name__)

# --- Logging Setup ---
handler = logging.StreamHandler(sys.stdout)
handler.setLevel(logging.INFO)
app.logger.addHandler(handler)
app.logger.setLevel(logging.INFO)

# --- CORS SETUP (CORRECTED) ---
CORS(app, origins=[
    "https://gleaming-brigadeiros-6bbd55.netlify.app",  # Parent App
    "https://darling-ganache-26a871.netlify.app",       # Driver App (THIS IS THE FIX)
    "https://chimerical-salamander-bf8231.netlify.app", # Admin App
    "null"
])

# --- Database Connection ---
db_url = os.environ.get("DATABASE_URL")
if not db_url:
    app.logger.critical("FATAL: DATABASE_URL environment variable not set.")
    sys.exit("FATAL: DATABASE_URL not found.")

try:
    app.db_pool = psycopg2.pool.SimpleConnectionPool(1, 10, dsn=db_url)
    app.logger.info("Database connection pool created successfully.")
except psycopg2.OperationalError as e:
    app.logger.critical(f"FATAL: Database connection failed: {e}")
    sys.exit("FATAL: Database connection failed.")


# --- In-memory store ---
bus_locations = {}

@app.route('/')
def index():
    return "Hello, World! The GPS server with DB connection is running."

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


# --- Bus Management ---
@app.route('/buses', methods=['GET', 'POST'])
def manage_buses():
    conn = None
    try:
        conn = app.db_pool.getconn()
        with conn.cursor(cursor_factory=DictCursor) as cur:
            if request.method == 'POST':
                data = request.get_json()
                bus_name = data.get('name')
                if not bus_name:
                    return jsonify({"error": "Bus name is required"}), 400
                
                cur.execute("INSERT INTO buses (name) VALUES (%s) ON CONFLICT (name) DO NOTHING;", (bus_name,))
                conn.commit()
                app.logger.info(f"Added or found bus: {bus_name}")

            cur.execute("SELECT id, name FROM buses ORDER BY name;")
            buses = [dict(row) for row in cur.fetchall()]
            return jsonify(buses)

    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Database error in /buses: {e}")
        return jsonify({"error": "A database error occurred."}), 500
    finally:
        if conn:
            app.db_pool.putconn(conn)

# --- Route and Stop Management ---

@app.route('/routes', methods=['GET', 'POST'])
def manage_routes():
    conn = None
    try:
        conn = app.db_pool.getconn()
        with conn.cursor(cursor_factory=DictCursor) as cur:
            if request.method == 'POST':
                data = request.get_json()
                route_name = data.get('name')
                if not route_name:
                    return jsonify({"error": "Route name is required"}), 400
                cur.execute("INSERT INTO routes (name) VALUES (%s) RETURNING id;", (route_name,))
                new_route_id = cur.fetchone()['id']
                conn.commit()
                app.logger.info(f"Created route '{route_name}' with ID {new_route_id}")
                return jsonify({"id": new_route_id, "name": route_name, "stops": []}), 201
            
            else: # GET request
                sql = """
                    SELECT
                        r.id as route_id, r.name as route_name,
                        s.sequence as stop_sequence, s.address as stop_address
                    FROM routes r
                    LEFT JOIN stops s ON r.id = s.route_id
                    ORDER BY r.id, s.sequence;
                """
                cur.execute(sql)
                results = cur.fetchall()
                
                routes_map = {}
                for row in results:
                    route_id = row['route_id']
                    if route_id not in routes_map:
                        routes_map[route_id] = {
                            'id': route_id,
                            'name': row['route_name'],
                            'stops': []
                        }
                    if row['stop_sequence'] is not None:
                        routes_map[route_id]['stops'].append({
                            'sequence': row['stop_sequence'],
                            'address': row['stop_address']
                        })
                
                return jsonify(list(routes_map.values()))

    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Database error in /routes: {e}")
        return jsonify({"error": f"A database error occurred: {e}"}), 500
    finally:
        if conn:
            app.db_pool.putconn(conn)


@app.route('/routes/<int:route_id>/stops', methods=['POST'])
def add_stop_to_route(route_id):
    conn = None
    try:
        conn = app.db_pool.getconn()
        with conn.cursor(cursor_factory=DictCursor) as cur:
            data = request.get_json()
            address = data.get('address')
            if not address:
                return jsonify({"error": "Address is required"}), 400

            cur.execute("SELECT COALESCE(MAX(sequence), 0) + 1 as next_seq FROM stops WHERE route_id = %s;", (route_id,))
            next_seq = cur.fetchone()['next_seq']
            
            cur.execute(
                "INSERT INTO stops (route_id, address, sequence) VALUES (%s, %s, %s) RETURNING sequence, address;",
                (route_id, address, next_seq)
            )
            new_stop = dict(cur.fetchone())
            conn.commit()
            app.logger.info(f"Added stop '{address}' to route {route_id} at sequence {next_seq}")
            return jsonify(new_stop), 201

    except Exception as e:
        if conn: conn.rollback()
        app.logger.error(f"Database error in /routes/.../stops: {e}")
        return jsonify({"error": "A database error occurred."}), 500
    finally:
        if conn:
            app.db_pool.putconn(conn)

if __name__ == '__main__':
    app.run(debug=True, port=5001)

