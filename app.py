from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import os
from dotenv import load_dotenv
from airtable_csv import AirtableCSVManager
import threading
from scheduler import DailyAirtableUpdater
from stripe_manager import create_checkout_session, create_payment_intent

app = Flask(__name__)
CORS(app)

load_dotenv('.env.local')

# Ensure required environment variables are set
if not os.getenv('AIRTABLE_BASE_ID') or not os.getenv('AIRTABLE_TABLE_NAME') or not os.getenv('AIRTABLE_API_KEY'):
    load_dotenv('.env')
if not os.getenv('AIRTABLE_BASE_ID') or not os.getenv('AIRTABLE_TABLE_NAME') or not os.getenv('AIRTABLE_API_KEY'):
    raise ValueError("Missing required environment variables: AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, AIRTABLE_API_KEY")

ENVIRONMENT_MODE = os.getenv('ENVIRONMENT', 'Production')

exporter = AirtableCSVManager(
    base_id=os.getenv('AIRTABLE_BASE_ID'),
    table_name=os.getenv('AIRTABLE_TABLE_NAME'),
    api_key=os.getenv('AIRTABLE_API_KEY')
)


@app.route("/")
def home():
    return "Hello, Flask!"


@app.route("/get-airtable-csv", methods=['GET'])
def get_airtable_csv():
    csv_data = exporter.read_csv()
    if not csv_data:
        return Response("No data found", status=404)
    return Response(csv_data, mimetype='text/csv')


@app.route("/update-tile-data", methods=['GET'])
def update_tile_data():
    success = exporter.update_csv_from_airtable()
    if success:
        return "CSV saved to /data/coastline-tiles-with-data.csv"
    else:
        return "No data found or failed to save", 500


@app.route("/get-tile-data", methods=['GET'])
def get_tile_data():
    json_data = exporter.convert_csv_to_json()
    if not json_data:
        return Response("No data found", status=404)
    return jsonify(json_data)

@app.route("/stripe/create-checkout-session", methods=['POST'])
def create_checkout_session_route():
    data = request.json
    price_id = data.get('price_id')
    success_url = data.get('success_url')
    cancel_url = data.get('cancel_url')
    quantity = data.get('quantity', 1)
    if not price_id or not success_url or not cancel_url:
        return jsonify({"error": "Missing required parameters"}), 400

    session = create_checkout_session(price_id, success_url, cancel_url, quantity)
    if session:
        return jsonify({"id": session.id})
    else:
        return jsonify({"error": "Failed to create checkout session"}), 500

@app.route("/stripe/create-payment-intent", methods=['POST'])
def create_payment_intent_route():
    data = request.json
    amount = data.get('amount')
    currency = data.get('currency', 'usd')
    metadata = data.get('metadata', {})
    if not amount:
        return jsonify({"error": "Missing required parameter: amount"}), 400
    payment_intent = create_payment_intent(amount, currency, metadata)
    if payment_intent:
        return jsonify({"id": payment_intent.id, "client_secret": payment_intent.client_secret})
    else:
        return jsonify({"error": "Failed to create payment intent"}), 500

if __name__ == '__main__':
    if ENVIRONMENT_MODE == 'Production':
        exporter.update_csv_from_airtable()  # Save initial CSV

    # Start the scheduler in a background thread
    def start_scheduler():
        updater = DailyAirtableUpdater()
        updater.run_daily("00:00")  # Set desired time

    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    app.run(debug=True)