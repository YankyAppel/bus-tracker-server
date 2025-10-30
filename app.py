from flask import Flask, request
from flask_cors import CORS
import logging

app = Flask(__name__)
CORS(app)

# Set up logging
logging.basicConfig(level=logging.INFO)

@app.route('/update_location', methods=['POST'])
def update_location():
    data = request.get_json()
    if not data:
        return 'No data received', 400

    bus_id = data.get('busId')
    lat = data.get('latitude')
    lon = data.get('longitude')

    if not all([bus_id, lat, lon]):
        return 'Missing data', 400

    # Log the received data to the Heroku logs
    app.logger.info(f'Received location for {bus_id}: Lat={lat}, Lon={lon}')

    # In a real app, you would save this to a database
    # For now, we just log it.

    return 'Location received', 200

if __name__ == '__main__':
    app.run(debug=True)

