from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import os
from airtable_multi_manager import AirtableMultiManager
from student_data_manager import StudentDataManager
import threading
from scheduler import DailyAirtableUploader
from utilities import load_env, deep_jsonify, parse_database_row, critical_tables

app = Flask(__name__)
CORS(app)

ENVIRONMENT_MODE = load_env('ENVIRONMENT_MODE')

# --- Initialisation ---

# Initialize AirtableCSVManager with environment variables
multi_manager = AirtableMultiManager.from_environment()

# Initialize StudentDataManager globally with error handling
student_data_manager = None
try:
    # Discover and add all tables from the base
    results = multi_manager.discover_and_add_tables_from_base()
    print(f"Added tables: {results}")
    
    # Check if database has data - only update from Airtable if empty
    database_has_data = multi_manager.sqlite_storage.has_data_in_critical_tables()
    
    if not database_has_data:
        print("Database appears empty - performing initial sync from Airtable")
        results = multi_manager.update_all_tables()
        print("Initial sync results: ", results)
        
        # Check if critical tables failed
        failed_critical = [table for table in critical_tables if table in results and 'Error' in str(results[table])]
        if failed_critical:
            print(f"Warning: Critical tables failed to update: {failed_critical}")
            
    else:
        print("Database has existing data - skipping initial sync from Airtable")
    
    # Set up StudentDataManager
    student_data_manager = StudentDataManager(multi_manager)

except Exception as e:
    print(f"Failed to initialize StudentDataManager: {e}")
    student_data_manager = None


def deep_jsonify_response(obj):
    """
    Helper function to deeply serialize complex objects before sending as JSON response
    """
    serialized = deep_jsonify(obj)
    return jsonify(serialized)


# --- Routes ---

@app.route("/")
def home():
    return "Up and running! View routes at: https://github.com/radkiwi/craffft-backend"


@app.route("/get-table-as-csv/<table_name>", methods=['GET'])
def get_airtable_csv(table_name):
    csv_data = multi_manager.get_csv_data(table_name)
    if not csv_data:
        return Response(f"No data found for table: {table_name}", status=404)
    return Response(csv_data, mimetype='text/csv')


@app.route("/update-server-from-airtable", methods=['GET'])
def update_server_from_airtable():
    results = multi_manager.update_all_tables()
    if results:
        return jsonify({
            "message": "All tables updated from Airtable",
            "results": results
        }), 200
    else:
        return Response(f"Failed to update from Airtable: {results}", status=500)


@app.route("/get-table-as-json/<table_name>", methods=['GET'])
def get_tile_data(table_name):
    json_data = multi_manager.convert_csv_to_json(table_name)
    if not json_data:
        return Response(f"No data found for table: {table_name}", status=404)
    return jsonify(json_data)

@app.route("/get-student-data-from-websiteId/<website_id>", methods=['GET'])
def get_student_data_from_website(website_id):
    if not website_id:
        return Response("Missing website_id parameter", status=400)

    # Get the manager for the craffft_students table
    manager = multi_manager.get_manager("craffft_students")
    if not manager:
        return Response("craffft_students table not found", status=404)

    # Look up the student by website_id
    student_row = manager.get_row("website_id", website_id)

    if not student_row:
        return Response(f"No student found with website_id: {website_id}", status=404)

    # Parse the database row to handle stringified lists
    parsed_row = parse_database_row(student_row)
    return jsonify(parsed_row)

@app.route("/get-student-data-from-record/<student_record>", methods=['GET'])
def get_student_data(student_record):
    if not student_record:
        return Response("Missing student_record parameter", status=400)

    # Get the manager for the craffft_students table
    manager = multi_manager.get_manager("craffft_students")
    if not manager:
        return Response("craffft_students table not found", status=404)
    
    # Look up the student by record_id
    student_row = manager.get_row("record_id", student_record)

    if not student_row:
        return Response(f"No student found with record_id: {student_record}", status=404)

    # Parse the database row to handle stringified lists
    parsed_row = parse_database_row(student_row)
    return jsonify(parsed_row)

@app.route("/get-value-from-db", methods=['POST'])
def get_value_from_db():
    data = request.get_json()
    if not data:
        return Response("Missing JSON body", status=400)
    table_name = data.get("table_name")
    reference_value = data.get("reference_value")
    target_column = data.get("target_column")
    column_containing_reference = data.get("column_containing_reference", "id")
    if not table_name or not reference_value:
        return Response("Missing required parameters: table_name and reference_value", status=400)
    if target_column:
        value = multi_manager.get_value(table_name, column_containing_reference, reference_value, target_column)
        if value is None:
            return Response(f"No value found for table: {table_name}, {column_containing_reference}: {reference_value}, column: {target_column}", status=404)
        return jsonify({target_column: value})
    else:
        manager = multi_manager.get_manager(table_name)
        if not manager:
            return Response(f"No manager found for table: {table_name}", status=404)
        row = manager.get_row(column_containing_reference, reference_value)
        if not row:
            return Response(f"No record found for table: {table_name}, {column_containing_reference}: {reference_value}", status=404)
        return jsonify(row)


@app.route("/get-student-data-dashboard/<classroom_id>", methods=['GET'])
def get_students_for_dashboard(classroom_id):
    if not classroom_id:
        return Response("Missing classroom_id parameter", status=400)

    if not student_data_manager:
        return Response("StudentDataManager not found", status=404)

    dashboard_info = student_data_manager.get_students_data_for_dashboard(classroom_id)
    if not dashboard_info:
        return Response(f"No data found for classroom_id: {classroom_id}", status=404)

    # Parse the dashboard info to handle stringified lists
    parsed_dashboard = deep_jsonify(dashboard_info, parse_stringified_lists=True)
    return jsonify(parsed_dashboard)

@app.route("/get-teacher-data/<id>", methods=['GET'])
def get_teacher_data(id):
    if not id:
        return Response("Missing id parameter", status=400)

    if not student_data_manager:
        return Response("StudentDataManager not found", status=404)

    teacher_info = student_data_manager.get_teacher_data(id)
    if not teacher_info:
        return Response(f"No data found for teacher_id: {id}", status=404)

    return jsonify(teacher_info)


@app.route("/modify-field", methods=['POST'])
def update_field():
    data = request.get_json()
    if not data:
        return Response("Missing JSON body", status=400)

    table_name = data.get("table_name")
    reference_value = data.get("reference_value")
    target_column = data.get("target_column")
    new_value = data.get("new_value")
    column_containing_reference = data.get("column_containing_reference", "id")

    if not table_name or not reference_value or not target_column or new_value is None:
        return Response("Missing required parameters: table_name, reference_value, target_column, new_value", status=400)

    manager = multi_manager.get_manager(table_name)
    if not manager:
        return Response(f"No manager found for table: {table_name}", status=404)

    success = manager.modify_field(column_containing_reference, reference_value, target_column, new_value)
    if success:
        return jsonify({"message": "Field updated successfully"})
    else:
        return Response(f"Failed to update field for table: {table_name}, {column_containing_reference}: {reference_value}, column: {target_column}", status=500)

@app.route("/update-student-current-step", methods=['GET'])
def update_student_current_step():
    # get websiteId and current-step as params
    website_id = request.args.get("websiteId")
    current_step = request.args.get("current-step")

    if not website_id or not current_step:
        return Response("Missing required parameters: websiteId, current-step", status=400)

    manager = multi_manager.get_manager("craffft_students")

    # First, verify the student exists
    student_row = manager.get_row("website_id", website_id)
    if not student_row:
        return Response(f"No student found with website_id: {website_id}", status=404)

    # Update the current_step field in the local database
    success = manager.modify_field("website_id", website_id, "current_step", current_step)
    if not success:
        return Response(f"Failed to update current_step for student with website_id: {website_id}", status=500)

    # Return success response
    return jsonify({
        "message": "Student current_step updated successfully",
        "website_id": website_id,
        "current_step": current_step,
        "local_update": "success"
    }), 200


@app.route("/upload-to-airtable", methods=['POST'])
def upload_to_airtable():
    """
    Upload all modified tables back to Airtable
    """
    results = multi_manager.upload_modified_tables_to_airtable()
    modified_tables = multi_manager.get_modified_tables()
    
    if not modified_tables:
        return jsonify({"message": "No tables have been modified", "results": results}), 200
    
    success_count = sum(1 for result in results.values() if result and not result.startswith("Error"))
    total_count = len(modified_tables)
    
    if success_count == total_count:
        return jsonify({
            "message": f"Successfully uploaded {success_count} modified tables to Airtable",
            "results": results
        }), 200
    else:
        return jsonify({
            "message": f"Uploaded {success_count}/{total_count} tables. Some uploads failed.",
            "results": results
        }), 207  # 207 = Multi-Status



@app.route("/get-modified-tables", methods=['GET'])
def get_modified_tables():
    """
    Get a list of tables that have been modified and need to be uploaded
    """
    modified_tables = multi_manager.get_modified_tables()
    return jsonify({
        "modified_tables": modified_tables,
        "count": len(modified_tables)
    })

# --- Scheduler Initialisation ---

if __name__ == '__main__':
    # Start the scheduler if in production mode
    if ENVIRONMENT_MODE == 'Production': 
        print("Starting scheduler for Production mode")
        
        # Start the scheduler in a background thread
        def start_scheduler():
            uploader = DailyAirtableUploader()
            uploader.run_daily("00:00")  # Set desired time

        scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
        scheduler_thread.start()

    app.run(debug=(ENVIRONMENT_MODE != 'Production'))