from flask import Flask, request, jsonify
from flask_cors import CORS
import psycopg2
import os
import bleach

app = Flask(__name__)

# Allow requests from your Netlify apps
CORS(app, origins=[
    "https://chimerical-salamander-bf8231.netlify.app",  # Admin App
    "https://darling-ganache-26a871.netlify.app",      # Driver App
    "https://gleaming-brigadeiros-6bbd55.netlify.app",   # Parent App
    "null" # Required for local file testing
])

def get_db_connection():
    """Establishes a connection to the database."""
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    return conn

@app.route('/buses', methods=['GET', 'POST'])
def handle_buses():
    """Handles GET and POST requests for the buses endpoint."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.get_json()
        bus_name = bleach.clean(data['name'])
        cursor.execute('INSERT INTO buses (name) VALUES (%s) RETURNING id, name;', (bus_name,))
        new_bus = cursor.fetchone()
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"id": new_bus[0], "name": new_bus[1]}), 201
    else: # GET request
        cursor.execute('SELECT id, name FROM buses ORDER BY name;')
        buses = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify([{"id": bus[0], "name": bus[1]} for bus in buses])

@app.route('/routes', methods=['GET', 'POST'])
def handle_routes():
    """Handles GET and POST requests for bus routes."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.get_json()
        bus_id = data.get('bus_id')
        name = bleach.clean(data['name'])
        cursor.execute('INSERT INTO routes (bus_id, name) VALUES (%s, %s) RETURNING id;', (bus_id, name))
        new_route_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"id": new_route_id}), 201
    else: # GET request
        bus_id = request.args.get('bus_id')
        query = 'SELECT r.id, r.name, b.name as bus_name FROM routes r JOIN buses b ON r.bus_id = b.id'
        params = []
        if bus_id:
            query += ' WHERE r.bus_id = %s'
            params.append(bus_id)
        query += ' ORDER BY r.name;'
        cursor.execute(query, tuple(params))
        routes = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"routes": [{"id": route[0], "name": route[1], "bus_name": route[2]} for route in routes]})

@app.route('/stops', methods=['GET', 'POST'])
def handle_stops():
    """Handles GET and POST requests for route stops."""
    conn = get_db_connection()
    cursor = conn.cursor()
    if request.method == 'POST':
        data = request.get_json()
        route_id = data['route_id']
        address = bleach.clean(data['address'])
        sequence = data['sequence']
        cursor.execute('INSERT INTO stops (route_id, address, sequence) VALUES (%s, %s, %s) RETURNING id;', (route_id, address, sequence))
        new_stop_id = cursor.fetchone()[0]
        conn.commit()
        cursor.close()
        conn.close()
        return jsonify({"id": new_stop_id}), 201
    else: # GET request
        route_id = request.args.get('route_id')
        cursor.execute('SELECT id, address, sequence FROM stops WHERE route_id = %s ORDER BY sequence;', (route_id,))
        stops = cursor.fetchall()
        cursor.close()
        conn.close()
        return jsonify({"stops": [{"id": stop[0], "address": stop[1], "sequence": stop[2]} for stop in stops]})

@app.route('/set_location', methods=['POST'])
def set_location():
    """Receives and stores the location of a bus."""
    data = request.get_json()
    bus_id = bleach.clean(data['bus_id'])
    lat = data['lat']
    lng = data['lng']
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        '''
        INSERT INTO locations (bus_id, lat, lng, timestamp) 
        VALUES (%s, %s, %s, NOW())
        ON CONFLICT (bus_id) 
        DO UPDATE SET lat = EXCLUDED.lat, lng = EXCLUDED.lng, timestamp = NOW();
        ''',
        (bus_id, lat, lng)
    )
    conn.commit()
    cursor.close()
    conn.close()
    return jsonify({"status": "success"}), 200

@app.route('/get_location')
def get_location():
    """Returns the last known location of a specific bus."""
    bus_id = bleach.clean(request.args.get('bus_id'))
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT lat, lng, timestamp FROM locations WHERE bus_id = %s;', (bus_id,))
    location = cursor.fetchone()
    cursor.close()
    conn.close()
    if location:
        return jsonify({"lat": location[0], "lng": location[1], "timestamp": location[2]})
    else:
        return jsonify({"error": "Bus location not found"}), 404

if __name__ == '__main__':
    app.run(debug=False)
