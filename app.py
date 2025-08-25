from flask import Flask, jsonify, request, Response, render_template, send_from_directory
from flask_cors import CORS
import os
from airtable_multi_manager import AirtableMultiManager
from student_data_manager import StudentDataManager
import threading
from scheduler import DailyAirtableUploader
from utilities import load_env, deep_jsonify, parse_database_row, critical_tables
from quest_routes import quest_bp

app = Flask(__name__)
CORS(app)

ENVIRONMENT_MODE = load_env('ENVIRONMENT_MODE')

# --- Initialisation ---

# Initialize TableManager with environment variables
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

# Store multi_manager in app config for use in blueprints
app.config['multi_manager'] = multi_manager

# Register quest routes blueprint
app.register_blueprint(quest_bp)


def deep_jsonify_response(obj):
    """
    Helper function to deeply serialize complex objects before sending as JSON response
    """
    serialized = deep_jsonify(obj)
    return jsonify(serialized)


# --- Routes ---

@app.route("/")
def home():
    return """
    <h1>Craffft Backend - Up and running!</h1>
    <p><a href="https://github.com/radkiwi/craffft-backend">View all routes on GitHub</a></p>
    <h2>Tools:</h2>
    <ul>
        <li><a href="/quest-generator">🎮 Quest Generator</a> - Create new quests and steps</li>
        <li><a href="/quest-browser">📖 Quest Browser</a> - View all created quests and steps</li>
    </ul>
    """


@app.route("/get-table-as-csv/<table_name>", methods=['GET'])
def get_table_manager(table_name):
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


@app.route("/update-and-check-quest", methods=['GET'])
def update_and_check_quest():
    """
    Update student's current step and check if quest changed
    
    Params:
        websiteId (required): Student's website ID
        current-step (required): New current step
        allow-quest-update (optional): Whether to update quest, defaults to true
    
    Returns:
        current_step: Student's current step
        current_quest: Student's current quest
        quest_changed: Boolean indicating if quest changed
    """
    # Get parameters
    website_id = request.args.get("websiteId")
    new_current_step = request.args.get("current-step")
    allow_quest_update = request.args.get("allow-quest-update", "true").lower() == "true"
    
    if not website_id or not new_current_step:
        return Response("Missing required parameters: websiteId, current-step", status=400)
    
    if not student_data_manager:
        return Response("StudentDataManager not found", status=500)
    
    # Use the StudentDataManager to handle the business logic
    result = student_data_manager.update_step_and_check_quest(
        website_id=website_id,
        new_current_step=new_current_step,
        allow_quest_update=allow_quest_update
    )
    
    if not result["success"]:
        return Response(result["error"], status=400)
    
    # Return the successful response
    return jsonify({
        "current_step": result["current_step"],
        "current_quest": result["current_quest"],
        "quest_changed": result["quest_changed"]
    })


@app.route("/add-students", methods=['POST'])
def add_students():
    """
    Add a list of students to the craffft_students table.
    
    Expected JSON format:
    {
        "students": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "gamer_tag": "johndoe123", 
                "website_id": 12345,
                "current_class": 1
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400
        
        students_list = data.get('students', [])
        if not students_list:
            return jsonify({"error": "Missing 'students' array in request"}), 400
        
        if not isinstance(students_list, list):
            return jsonify({"error": "'students' must be an array"}), 400
        
        # Get the students table manager
        students_manager = multi_manager.get_manager("craffft_students")
        if not students_manager:
            return jsonify({"error": "craffft_students table not found"}), 404
        
        added_students = []
        failed_students = []
        
        for i, student in enumerate(students_list):
            try:
                # Validate required fields
                required_fields = ['first_name', 'last_name', 'gamer_tag', 'website_id', 'current_class']
                missing_fields = [field for field in required_fields if field not in student or student.get(field) is None]
                
                if missing_fields:
                    failed_students.append({
                        "index": i,
                        "student": student,
                        "error": f"Missing required fields: {', '.join(missing_fields)}"
                    })
                    continue
                
                # Validate data types
                if not isinstance(student['website_id'], int):
                    failed_students.append({
                        "index": i,
                        "student": student,
                        "error": "website_id must be an integer"
                    })
                    continue
                    
                if not isinstance(student['current_class'], int):
                    failed_students.append({
                        "index": i,
                        "student": student,
                        "error": "current_class must be an integer"
                    })
                    continue
                
                # Generate record ID
                import uuid
                record_id = f"rec{str(uuid.uuid4()).replace('-', '')[:10]}"
                
                # Create student record based on your table structure
                student_record = {
                    'record_id': record_id,
                    'first_name': student['first_name'].strip(),
                    'last_name': student['last_name'].strip(),
                    'gamer_tag': student['gamer_tag'].strip(),
                    'website_id': str(student['website_id']),  # Convert int to string for database
                    'current_class': str(student['current_class']),  # Convert int to string for database
                    # Set default values for other fields based on your table structure
                    'current_quest': student.get('current_quest', ''),
                    'current_step': student.get('current_step', ''),
                    'quest_progress_percentage': '0' # Default to 0
                }
                
                # Add the student to the database
                success = students_manager.add_record(student_record)
                
                if success:
                    added_students.append({
                        "record_id": record_id,
                        "first_name": student['first_name'],
                        "last_name": student['last_name'],
                        "gamer_tag": student['gamer_tag'],
                        "website_id": student['website_id']  # Keep as integer in response
                    })
                else:
                    failed_students.append({
                        "index": i,
                        "student": student,
                        "error": "Failed to add to database"
                    })
                    
            except Exception as e:
                failed_students.append({
                    "index": i,
                    "student": student,
                    "error": f"Unexpected error: {str(e)}"
                })
        
        # Mark table as modified for Airtable sync
        if added_students:
            multi_manager.mark_table_as_modified("craffft_students")
        
        # Prepare response
        response_data = {
            "message": f"Processed {len(students_list)} students",
            "added_count": len(added_students),
            "failed_count": len(failed_students),
            "added_students": added_students
        }
        
        if failed_students:
            response_data["failed_students"] = failed_students
        
        status_code = 201 if len(added_students) > 0 else 400
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/assign-quests", methods=['POST'])
def assign_quests():
    """
    Assign quests to multiple students.
    
    Expected JSON format:
    {
        "assignments": [
            {
                "websiteId": 12345,
                "quest_name": "Garlic Guardians"
            },
            {
                "websiteId": 12346,
                "quest_name": "Electric Orchard"
            }
        ]
    }
    """
    try:
        data = request.get_json()
        assignments = data.get('assignments', [])
        
        if not assignments:
            return jsonify({"error": "Missing 'assignments' array"}), 400
        
        students_manager = multi_manager.get_manager("craffft_students")
        successful_assignments = []
        failed_assignments = []
        
        for assignment in assignments:
            website_id = assignment.get('websiteId')
            quest_name = assignment.get('quest_name')
            
            if not website_id or not quest_name:
                failed_assignments.append(assignment)
                continue
            
            # Assign the quest
            success = students_manager.modify_field(
                column_containing_reference="website_id",
                reference_value=str(website_id),
                target_column="current_quest",
                new_value=quest_name
            )
            
            if success:
                successful_assignments.append({
                    "websiteId": website_id,
                    "quest_name": quest_name
                })
            else:
                failed_assignments.append(assignment)
        
        # Mark table as modified for Airtable sync
        if successful_assignments:
            multi_manager.mark_table_as_modified("craffft_students")
        
        return jsonify({
            "successful_count": len(successful_assignments),
            "failed_count": len(failed_assignments),
            "successful_assignments": successful_assignments,
            "failed_assignments": failed_assignments
        }), 200
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/upload-to-airtable", methods=['POST'])
def upload_to_airtable():
    """
    Upload all modified tables back to Airtable, or upload a specific table if specified
    """

    force_upload = request.args.get("force_upload", default=False, type=bool)
    table_name = request.args.get("table_name")

    # If a specific table is requested
    if table_name:
        # Check if the table exists
        manager = multi_manager.get_manager(table_name)
        if not manager:
            return Response(f"Table '{table_name}' not found", status=404)
        
        # Upload the specific table
        if force_upload:
            # Mark as modified to ensure upload happens
            multi_manager.mark_table_as_modified(table_name)
        
        result = multi_manager.upload_table_to_airtable(table_name)
        
        if result and not result.startswith("Error"):
            return jsonify({
                "message": f"Successfully uploaded table '{table_name}' to Airtable",
                "table": table_name,
                "result": result
            }), 200
        else:
            return jsonify({
                "message": f"Failed to upload table '{table_name}' to Airtable",
                "table": table_name,
                "result": result
            }), 500
    
    # Otherwise, upload all modified tables (existing behavior)
    results = multi_manager.upload_modified_tables_to_airtable(force_upload=force_upload)
    modified_tables = multi_manager.get_modified_tables()
    
    if not modified_tables and not force_upload:
        return jsonify({"message": "No tables have been modified", "results": results}), 200
    
    success_count = sum(1 for result in results.values() if result and not result.startswith("Error"))
    total_count = len(modified_tables) if not force_upload else len(results)
    
    if success_count == total_count:
        return jsonify({
            "message": f"Successfully uploaded {success_count} {'modified ' if not force_upload else ''}tables to Airtable",
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