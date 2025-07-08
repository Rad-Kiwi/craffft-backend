from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import os
from dotenv import load_dotenv
from airtable_multi_manager import AirtableMultiManager
import threading
from scheduler import DailyAirtableUpdater

app = Flask(__name__)
CORS(app)

load_dotenv('.env.local')

# Ensure required environment variables are set
if not os.getenv('AIRTABLE_BASE_ID') or not os.getenv('AIRTABLE_API_KEY'):
    load_dotenv('.env')
if not os.getenv('AIRTABLE_BASE_ID') or not os.getenv('AIRTABLE_API_KEY'):
    raise ValueError("Missing required environment variables: AIRTABLE_BASE_ID, AIRTABLE_TABLE_NAME, AIRTABLE_API_KEY")

ENVIRONMENT_MODE = os.getenv('ENVIRONMENT', 'Production')

# Initialize AirtableCSVManager with environment variables
multi_manager = AirtableMultiManager.from_environment()


@app.route("/")
def home():
    return "Hello, Flask!"


@app.route("/get-table-as-csv/<table_name>", methods=['GET'])
def get_airtable_csv(table_name):
    csv_data = multi_manager.get_csv_data(table_name)
    if not csv_data:
        return Response(f"No data found for table: {table_name}", status=404)
    return Response(csv_data, mimetype='text/csv')


@app.route("/update-server-from-airtable", methods=['GET'])
def update_server_from_airtable():
    success = multi_manager.update_all_tables()
    if success:
        return "CSV saved to /data/<your_table_name>.csv", 200
    else:
        return Response(f"Failed to update CSV from Airtable: {results}", status=500)


@app.route("/get-table-as-json/<table_name>", methods=['GET'])
def get_tile_data(table_name):
    json_data = multi_manager.convert_csv_to_json(table_name)
    if not json_data:
        return Response(f"No data found for table: {table_name}", status=404)
    return jsonify(json_data)


if __name__ == '__main__':

    # Discover and add all tables from the base
    results = multi_manager.discover_and_add_tables_from_base()
    print(f"Added tables: {results}")

    # If in production mode, update all tables
    if ENVIRONMENT_MODE == 'Production':
        results = multi_manager.update_all_tables()
        print("All tables updated successfully: ", results)
    
    # Start the scheduler in a background thread
    def start_scheduler():
        updater = DailyAirtableUpdater()
        updater.run_daily("00:00")  # Set desired time

    scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
    scheduler_thread.start()

    app.run(debug=True)