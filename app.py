# Python Bus Tracking Script
# This script creates a simple web application using Flask that can be used
# with Twilio to provide bus ETAs to parents.

# --- Core Libraries ---
from flask import Flask, request
from twilio.twiml.voice_response import VoiceResponse
import requests
import os

# --- Flask App Initialization ---
app = Flask(__name__)

# --- Configuration (Best stored as environment variables) ---
# You will get these from your service providers.
# A developer will know how to set these up on a server.
GOOGLE_MAPS_API_KEY = os.environ.get("GOOGLE_MAPS_API_KEY", "YOUR_GOOGLE_MAPS_API_KEY")
GPS_PROVIDER_API_KEY = os.environ.get("GPS_PROVIDER_API_KEY", "YOUR_GPS_PROVIDER_API_KEY")
GPS_PROVIDER_API_URL = "https://api.yourgpstracker.com/v1/location/" # Placeholder URL

# --- Placeholder Data (Replace with a real database or Google Sheet) ---
# This data links a parent's phone number to their child's route and home address.
# The key is the parent's phone number (e.g., "+15551234567")
# 'route_id' corresponds to the bus.
# 'tracker_id' is the ID of the GPS device on that bus.
PARENT_DATA = {
    "+18455403984": { # Example using your number
        "address": "134 S 9th St, Brooklyn, NY 11249",
        "route_id": "1",
        "tracker_id": "BUS_TRACKER_01"
    }
    # Add more parents here
}

# --- Main Application Endpoint ---
# Twilio will send a request to this URL when a parent calls.
@app.route("/voice", methods=['GET', 'POST'])
def voice():
    """Responds to incoming phone calls with a spoken ETA."""
    
    # Create a TwiML response object
    resp = VoiceResponse()
    
    # Get the parent's phone number from the Twilio request
    caller_number = request.values.get('From', None)
    
    if caller_number in PARENT_DATA:
        # --- 1. Get Parent and Bus Info ---
        parent = PARENT_DATA[caller_number]
        destination_address = parent["address"]
        tracker_id = parent["tracker_id"]
        
        try:
            # --- 2. Get Bus's Current Location ---
            # This is a MOCK request. A developer will need to adapt this
            # to the actual API of your chosen GPS provider.
            gps_response = requests.get(
                f"{GPS_PROVIDER_API_URL}{tracker_id}",
                headers={"Authorization": f"Bearer {GPS_PROVIDER_API_KEY}"}
            )
            gps_response.raise_for_status() # Raises an error if the request failed
            bus_location = gps_response.json() # Expects format like {"lat": 40.7128, "lon": -74.0060}
            bus_origin = f'{'''{bus_location["lat"]},{bus_location["lon"]}'''}'

            # --- 3. Get ETA from Google Maps ---
            maps_url = "https://maps.googleapis.com/maps/api/distancematrix/json"
            params = {
                "origins": bus_origin,
                "destinations": destination_address,
                "key": GOOGLE_MAPS_API_KEY,
                "units": "imperial" # for minutes
            }
            maps_response = requests.get(maps_url, params=params)
            maps_response.raise_for_status()
            maps_data = maps_response.json()
            
            # Extract the travel time from the Google Maps response
            eta_text = maps_data["rows"][0]["elements"][0]["duration"]["text"]
            
            # --- 4. Prepare and Speak the Response ---
            message = f"The bus is approximately {eta_text} away."
            resp.say(message, voice='alice')

        except requests.exceptions.RequestException as e:
            # Handle errors if API calls fail
            resp.say("Sorry, I could not retrieve the bus location at this time.", voice='alice')
        except (KeyError, IndexError):
            # Handle errors if the response format is not what we expect
            resp.say("Sorry, there was an error processing the location data.", voice='alice')

    else:
        # If the caller is not recognized
        resp.say("Welcome. This service is for authorized parents only.", voice='alice')

    # Return the TwiML response to Twilio
    return str(resp)

# --- Standard Flask entry point ---
if __name__ == "__main__":
    # This allows the app to be run locally for testing
    app.run(debug=True)
