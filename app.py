from flask import Flask, jsonify, request, Response
from flask_cors import CORS
import os
from airtable_multi_manager import AirtableMultiManager
from student_data_manager import StudentDataManager
import threading
from scheduler import DailyAirtableUpdater
from utilities import load_env, deep_jsonify, parse_database_row

app = Flask(__name__)
CORS(app)

ENVIRONMENT_MODE = load_env('ENVIRONMENT_MODE')

# Initialize AirtableCSVManager with environment variables
multi_manager = AirtableMultiManager.from_environment()


def deep_jsonify_response(obj):
    """
    Helper function to deeply serialize complex objects before sending as JSON response
    """
    serialized = deep_jsonify(obj)
    return jsonify(serialized)


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

@app.route("/get-student-data/<student_record>", methods=['GET'])
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


if __name__ == '__main__':

    # Discover and add all tables from the base
    results = multi_manager.discover_and_add_tables_from_base()
    print(f"Added tables: {results}")


    # If in production mode, update all tables
    if ENVIRONMENT_MODE == 'Production':
        print("Running in Production mode")

        results = multi_manager.update_all_tables()
        print("All tables updated successfully: ", results)
    
        # Start the scheduler in a background thread
        def start_scheduler():
            updater = DailyAirtableUpdater()
            updater.run_daily("00:00")  # Set desired time

        scheduler_thread = threading.Thread(target=start_scheduler, daemon=True)
        scheduler_thread.start()

    # Set up StudentDataManager
    try:
        student_data_manager = StudentDataManager(multi_manager)
        print("StudentDataManager initialized successfully")
    except Exception as e:
        print(f"Failed to initialize StudentDataManager: {e}")
        student_data_manager = None

    app.run(debug=(ENVIRONMENT_MODE != 'Production'))