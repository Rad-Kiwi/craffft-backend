from flask import Flask, jsonify, request, Response, render_template, send_from_directory
from flask_cors import CORS
import os
from airtable_multi_manager import AirtableMultiManager
from student_data_manager import StudentDataManager
import threading
from scheduler import DailyAirtableUploader
from utilities import load_env, deep_jsonify, parse_database_row, critical_tables, is_ci_testing_mode
from quest_routes import quest_bp
from admin_routes import admin_bp
import uuid

app = Flask(__name__)
CORS(app)

# Configure session for admin authentication
app.secret_key = os.environ.get('SECRET_KEY', 'dev-secret-key-change-in-production')

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
    
    # Skip Airtable sync in CI testing mode
    if is_ci_testing_mode():
        print("CI Testing Mode: Skipping Airtable sync - using mock data")
        student_data_manager = StudentDataManager(multi_manager)
    else:
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

# Register admin routes blueprint
app.register_blueprint(admin_bp)


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
    <h2>API Documentation:</h2>
    <ul>
        <li><a href="/docs/">📚 Interactive API Documentation (Swagger)</a> - Test all endpoints with live examples</li>
    </ul>
    <h2>Tools:</h2>
    <ul>
        <li><a href="/quest-generator">🎮 Quest Generator</a> - Create new quests and steps</li>
        <li><a href="/quest-browser">📖 Quest Browser</a> - View all created quests and steps</li>
    </ul>
    """


@app.route("/data/csv/<table_name>", methods=['GET'])
@app.route("/get-table-as-csv/<table_name>", methods=['GET'])
def get_table_manager(table_name):
    csv_data = multi_manager.get_csv_data(table_name)
    if not csv_data:
        return Response(f"No data found for table: {table_name}", status=404)
    return Response(csv_data, mimetype='text/csv')


@app.route("/sync/update-all", methods=['POST'])
@app.route("/update-server-from-airtable", methods=['POST'])
def update_server_from_airtable():
    results = multi_manager.update_all_tables()
    if results:
        return jsonify({
            "message": "All tables updated from Airtable",
            "results": results
        }), 200
    else:
        return Response(f"Failed to update from Airtable: {results}", status=500)

@app.route("/sync/update-table", methods=['POST'])
@app.route("/update-table-from-airtable", methods=['POST'])
def update_table_from_airtable():
    """
    Update specific table(s) from Airtable.
    
    Expected JSON format:
    {
        "table_name": "craffft_students",  // Required
        "force_delete": true  // Optional, defaults to true
    }
    
    Or use query parameters: /update-table-from-airtable?table_name=craffft_students&force_delete=true
    """
    try:
        # Get table name from JSON body or query parameter
        table_name = None
        force_delete = True  # Default to true for safety
        
        if request.is_json:
            data = request.get_json()
            if data:
                table_name = data.get('table_name')
                force_delete = data.get('force_delete', True)  # Default to True
        
        if not table_name:
            table_name = request.args.get('table_name')
        if request.args.get('force_delete') is not None:
            force_delete = request.args.get('force_delete', 'true').lower() == 'true'
        
        if table_name:
            # Update specific table
            manager = multi_manager.get_manager(table_name)
            if not manager:
                return jsonify({"error": f"Table '{table_name}' not found"}), 404
            
            result = manager.update_database_from_airtable(force_delete=force_delete)
            
            if result and not str(result).startswith("Error"):
                response_message = f"Table '{table_name}' updated successfully from Airtable"
                if force_delete:
                    response_message += " (table was deleted and recreated)"
                    
                return jsonify({
                    "message": response_message,
                    "table": table_name,
                    "force_delete": force_delete,
                    "result": result
                }), 200
            else:
                return jsonify({
                    "error": f"Failed to update table '{table_name}' from Airtable",
                    "result": result
                }), 500
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/data/json/<table_name>", methods=['GET'])
@app.route("/get-table-as-json/<table_name>", methods=['GET'])
def get_tile_data(table_name):
    """
    Get all data from a specified table.
    
    Args:
        table_name: Name of the table to retrieve data from
    
    Returns:
        All table data as JSON array with parsed stringified fields
    """
    try:
        # Get the table manager
        table_manager = multi_manager.get_manager(table_name)
        if not table_manager:
            return jsonify({"error": f"{table_name} table not found"}), 404
        
        # Get all data using the table manager's method that handles JSON parsing
        parsed_data = table_manager.get_table_as_json_data()
        
        if not parsed_data:
            return jsonify({"error": f"No data found for table: {table_name}"}), 404
        
        return jsonify(parsed_data), 200
        
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500



@app.route("/students/get-by-website-id/<website_id>", methods=['GET'])
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

@app.route("/students/get-by-record/<student_record>", methods=['GET'])
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

@app.route("/data/query", methods=['POST'])
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


@app.route("/students/dashboard/<classroom_id>", methods=['GET'])
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

@app.route("/teachers/get/<id>", methods=['GET'])
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

@app.route("/teacher/add", methods=['POST'])
@app.route("/add-teacher", methods=['POST'])
def add_teacher():
    """
    Add a teacher to the craffft_teachers table.
    
    Expected JSON format:
    {
        "website_user_id": "12345",
        "first_name": "John",
        "last_name": "Smith",
        "school_name": "Example School"  // optional
    }
    """
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON body"}), 400

    # Validate required fields
    required_fields = ['website_user_id', 'first_name', 'last_name']
    missing_fields = [field for field in required_fields if not data.get(field)]
    
    if missing_fields:
        return jsonify({"error": f"Missing required fields: {', '.join(missing_fields)}"}), 400
    
    # Get the teachers table manager
    teachers_manager = multi_manager.get_manager("craffft_teachers")
    
    # Check if teacher already exists
    existing_teacher = teachers_manager.get_row("website_user_id", str(data['website_user_id']))
    if existing_teacher:
        return jsonify({
            "error": f"Teacher with website_user_id {data['website_user_id']} already exists"
        }), 409  # Conflict
    
    # Generate record ID
    record_id = f"rec{str(uuid.uuid4()).replace('-', '')[:10]}"
    
    # Create teacher record
    teacher_record = {
        'record_id': record_id,
        'website_user_id': str(data['website_user_id']),
        'first_name': data['first_name'].strip(),
        'last_name': data['last_name'].strip(),
        'school_name': data.get('school_name', '').strip() if data.get('school_name') else ''
    }
    
    # Add the teacher to the database
    success = teachers_manager.add_record(teacher_record)
    
    if success:
        # Mark table as modified for Airtable sync
        multi_manager.mark_table_as_modified("craffft_teachers")
        
        return jsonify({
            "message": "Teacher added successfully",
            "teacher": {
                "record_id": record_id,
                "website_user_id": data['website_user_id'],
                "first_name": data['first_name'],
                "last_name": data['last_name'],
                "school_name": teacher_record['school_name']
            }
        }), 201
    else:
        return jsonify({"error": "Failed to add teacher to database"}), 500


@app.route("/quests/steps", methods=['GET'])
@app.route("/get-step-data", methods=['GET'])
def get_step_data():
    """
    Get step data from craffft_steps table.
    
    Query parameters:
        step (optional): Name of specific step to retrieve. If not provided, returns all steps.
    
    Returns:
        - If step parameter provided: Single step data as JSON
        - If no parameter: All steps data as JSON array
    """
    try:
        # Get the steps table manager
        steps_manager = multi_manager.get_manager("craffft_steps")
        if not steps_manager:
            return jsonify({"error": "craffft_steps table not found"}), 404
        
        # Get step parameter from query string
        step_name = request.args.get('step')
        
        if step_name:
            # Return specific step by name
            step_row = steps_manager.get_row("name", step_name)
            if not step_row:
                return jsonify({"error": f"Step '{step_name}' not found"}), 404
            
            # Parse the step row to handle stringified data
            parsed_step = parse_database_row(step_row)
            return jsonify(parsed_step), 200
        else:
            # Return all steps
            json_data = multi_manager.get_table_as_json("craffft_steps")
            if not json_data:
                return jsonify({"error": "No step data found"}), 404
            
            # Parse all steps to handle stringified data
            parsed_steps = []
            for step in json_data:
                parsed_step = parse_database_row(step)
                parsed_steps.append(parsed_step)
            
            return jsonify(parsed_steps), 200
            
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/data/modify-field", methods=['POST'])
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

@app.route("/students/update-current-step", methods=['GET'])
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


@app.route("/students/update-and-check-quest", methods=['GET'])
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
        "quest_changed": result["quest_changed"],
        "quest_completed": result.get("quest_completed", False)
    })


@app.route("/students/add", methods=['POST'])
@app.route("/add-students", methods=['POST'])
def add_students():
    """
    Add a list of students to the craffft_students table.
    
    Expected JSON format:
    {
        "teacher_website_id": "123",
        "add_classes_to_teacher": true,
        "students": [
            {
                "first_name": "John",
                "last_name": "Doe",
                "gamer_tag": "johndoe123",  // optional
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

        teacher_website_id = data.get('teacher_website_id', '')
        # Ensure teacher_website_id is always a string
        if isinstance(teacher_website_id, int):
            teacher_website_id = str(teacher_website_id)
        add_classes_to_teacher = data.get('add_classes_to_teacher', False)
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
                # Validate required fields (gamer_tag is now optional)
                required_fields = ['first_name', 'last_name', 'website_id', 'current_class']
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
                    
                    failed_students.append({
                        "index": i,
                        "student": student,
                        "error": "current_class must be an integer"
                    })
                    continue
                
                # Generate record ID
                record_id = f"rec{str(uuid.uuid4()).replace('-', '')[:10]}"
                
                # Create student record based on your table structure
                student_record = {
                    'record_id': record_id,
                    'first_name': student['first_name'].strip(),
                    'last_name': student['last_name'].strip(),
                    'gamer_tag': student.get('gamer_tag', '').strip() if student.get('gamer_tag') else '',
                    'website_id': str(student['website_id']),  # Convert int to string for database
                    'current_class': f"{teacher_website_id}>{str(student['current_class'])}",  # Use teacher_website_id instead of name
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
                        "gamer_tag": student.get('gamer_tag', ''),
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
        
        # Add classes to teacher if requested and students were successfully added
        teacher_update_result = None
        if add_classes_to_teacher and teacher_website_id and added_students and student_data_manager:
            # Collect unique class IDs from successfully added students
            class_ids = set()
            for student in students_list:
                if 'current_class' in student:
                    class_ids.add(str(student['current_class']))
            
            if class_ids:
                teacher_update_result = student_data_manager.add_classes_to_teacher_by_website_id(
                    teacher_website_id=teacher_website_id,
                    new_classes=class_ids
                )
        
        # Prepare response
        response_data = {
            "message": f"Processed {len(students_list)} students",
            "added_count": len(added_students),
            "failed_count": len(failed_students),
            "added_students": added_students
        }
        
        if failed_students:
            response_data["failed_students"] = failed_students
        
        # Add teacher update information to response if applicable
        if teacher_update_result:
            response_data["teacher_update"] = teacher_update_result
        
        status_code = 201 if len(added_students) > 0 else 400
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/students/delete", methods=['DELETE'])
@app.route("/delete-students", methods=['DELETE'])
def delete_students():
    """
    Delete multiple students by their website IDs.
    
    Expected JSON format:
    {
        "website_ids": [12345, 12346, 12347]
    }
    """
    data = request.get_json()
    if not data or not data.get('website_ids'):
        return jsonify({"error": "Missing 'website_ids' array"}), 400
    
    website_ids = data['website_ids']
    students_manager = multi_manager.get_manager("craffft_students")
    
    deleted = []
    failed = []
    
    for website_id in website_ids:
        website_id_str = str(website_id)
        
        # Get student info before deletion
        student = students_manager.get_row("website_id", website_id_str)
        if not student:
            failed.append({"website_id": website_id, "error": "Student not found"})
            continue
        
        # Delete the student
        if students_manager.delete_record("website_id", website_id_str):
            deleted.append({
                "website_id": website_id,
                "name": f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()
            })
        else:
            failed.append({"website_id": website_id, "error": "Delete failed"})
    
    # Mark table for Airtable sync
    if deleted:
        multi_manager.mark_table_as_modified("craffft_students")
    
    # Determine appropriate status code
    if not deleted and not failed:
        # No website_ids provided or empty array
        status_code = 400
    elif deleted and not failed:
        # All deletions successful
        status_code = 200
    elif not deleted and failed:
        # All deletions failed (students not found or delete errors)
        status_code = 404 if all("not found" in f.get("error", "").lower() for f in failed) else 422
    else:
        # Mixed results (some succeeded, some failed)
        status_code = 207  # Multi-Status
    
    return jsonify({
        "deleted": len(deleted),
        "failed": len(failed),
        "deleted_students": deleted,
        "failed_deletions": failed if failed else None
    }), status_code


@app.route("/students/modify", methods=['PUT'])
@app.route("/modify-students", methods=['PUT'])
def modify_students():
    """
    Modify student names by their website IDs.
    
    Expected JSON format:
    {
        "students": [
            {
                "website_id": 12345,
                "first_name": "NewFirstName",
                "last_name": "NewLastName"
            },
            {
                "website_id": 12346,
                "first_name": "AnotherFirst"
                // last_name is optional - only provided fields will be updated
            }
        ]
    }
    """
    data = request.get_json()
    if not data or not data.get('students'):
        return jsonify({"error": "Missing 'students' array"}), 400
    
    students_list = data['students']
    students_manager = multi_manager.get_manager("craffft_students")
    
    modified = []
    failed = []
    
    for student_update in students_list:
        website_id = student_update.get('website_id')
        if not website_id:
            failed.append({"student": student_update, "error": "Missing website_id"})
            continue
            
        website_id_str = str(website_id)
        
        # Check if student exists
        student = students_manager.get_row("website_id", website_id_str)
        if not student:
            failed.append({"website_id": website_id, "error": "Student not found"})
            continue
        
        # Update first_name if provided
        updates_made = []
        if 'first_name' in student_update:
            if students_manager.modify_field("website_id", website_id_str, "first_name", student_update['first_name']):
                updates_made.append("first_name")
            else:
                failed.append({"website_id": website_id, "error": "Failed to update first_name"})
                continue
        
        # Update last_name if provided
        if 'last_name' in student_update:
            if students_manager.modify_field("website_id", website_id_str, "last_name", student_update['last_name']):
                updates_made.append("last_name")
            else:
                failed.append({"website_id": website_id, "error": "Failed to update last_name"})
                continue
        
        if updates_made:
            modified.append({
                "website_id": website_id,
                "updated_fields": updates_made,
                "new_name": f"{student_update.get('first_name', student.get('first_name', ''))} {student_update.get('last_name', student.get('last_name', ''))}".strip()
            })
    
    # Mark table for Airtable sync
    if modified:
        multi_manager.mark_table_as_modified("craffft_students")
    
    # Determine appropriate status code
    if not modified and not failed:
        # No valid updates requested
        status_code = 400
    elif modified and not failed:
        # All modifications successful
        status_code = 200
    elif not modified and failed:
        # All modifications failed
        status_code = 404 if all("not found" in f.get("error", "").lower() for f in failed) else 422
    else:
        # Mixed results (some succeeded, some failed)
        status_code = 207  # Multi-Status
    
    return jsonify({
        "modified": len(modified),
        "failed": len(failed),
        "modified_students": modified,
        "failed_modifications": failed if failed else None
    }), status_code


@app.route("/quests/assign", methods=['POST'])
@app.route("/assign-quests", methods=['POST'])
def assign_quests():
    """
    Assign quests to multiple students.
    
    Expected JSON format:
    {
        "assignments": [
            {
                "websiteId": 12345,
                "quest_code": "GG"
            },
            {
                "websiteId": 12346,
                "quest_code": "EO"
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
            quest_code = assignment.get('quest_code')

            if not website_id or not quest_code:
                failed_assignments.append(assignment)
                continue
            
            # Assign the quest
            success = students_manager.modify_field(
                column_containing_reference="website_id",
                reference_value=str(website_id),
                target_column="current_quest",
                new_value=quest_code
            )
            
            if success:
                successful_assignments.append({
                    "websiteId": website_id,
                    "quest_code": quest_code
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


@app.route("/quests/assign-to-class", methods=['POST'])
@app.route("/assign-quest-to-class", methods=['POST'])
def assign_quest_to_class():
    """
    Assign a quest to all students in a given class.
    
    Expected JSON format:
    {
        "class_name": "15>1",
        "quest_code": "GG"
    }
    
    Or use query parameters: /assign-quest-to-class?class_name=15>1&quest_code=GG
    """
    try:
        # Get parameters from JSON body or query parameters
        class_name = None
        quest_code = None
        
        if request.is_json:
            data = request.get_json()
            if data:
                class_name = data.get('class_name')
                quest_code = data.get('quest_code')
        
        if not class_name:
            class_name = request.args.get('class_name')
        if not quest_code:
            quest_code = request.args.get('quest_code')
        
        if not class_name or not quest_code:
            return jsonify({"error": "Missing required parameters: class_name and quest_code"}), 400
        
        # Get the students table manager
        students_manager = multi_manager.get_manager("craffft_students")
        
        # Find all students in the given class using the new get_rows method
        students_in_class = students_manager.get_rows("current_class", class_name)
        
        if not students_in_class:
            return jsonify({
                "message": f"No students found in class '{class_name}'",
                "class_name": class_name,
                "quest_code": quest_code,
                "students_found": 0,
                "successful_assignments": 0,
                "failed_assignments": 0
            }), 200
        
        successful_assignments = []
        failed_assignments = []
        
        # Assign the quest to each student in the class
        for student in students_in_class:
            try:
                website_id = student.get('website_id')
                student_name = f"{student.get('first_name', '')} {student.get('last_name', '')}".strip()
                
                if not website_id:
                    failed_assignments.append({
                        "student": student_name,
                        "error": "Missing website_id"
                    })
                    continue
                
                # Reset quest fields and assign new quest using StudentDataManager
                success = student_data_manager.reset_student_quest(str(website_id), quest_code)
                
                if success:
                    successful_assignments.append({
                        "website_id": website_id,
                        "student_name": student_name,
                        "quest_code": quest_code
                    })
                else:
                    failed_assignments.append({
                        "website_id": website_id,
                        "student_name": student_name,
                        "error": "Failed to update quest in database"
                    })
                    
            except Exception as e:
                failed_assignments.append({
                    "student": student.get('first_name', 'Unknown'),
                    "error": f"Unexpected error: {str(e)}"
                })
        
        # Mark table as modified for Airtable sync if any assignments were successful
        if successful_assignments:
            multi_manager.mark_table_as_modified("craffft_students")
        
        # Prepare response
        response_data = {
            "message": f"Processed quest assignment for class '{class_name}'",
            "class_name": class_name,
            "quest_code": quest_code,
            "students_found": len(students_in_class),
            "successful_assignments": len(successful_assignments),
            "failed_assignments": len(failed_assignments),
            "successful_students": successful_assignments
        }
        
        if failed_assignments:
            response_data["failed_students"] = failed_assignments
        
        status_code = 200 if len(successful_assignments) > 0 else 400
        return jsonify(response_data), status_code
        
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/quests/assign-achievement", methods=['POST'])
@app.route("/assign-achievement-to-student", methods=['POST'])
def assign_achievement_to_student():
    """
    Assign an achievement to a student.
    
    Expected JSON format:
    {
        "websiteId": 12345,
        "achievement_name": "First Quest Complete"
    }
    
    Or use query parameters: /assign-achievement-to-student?websiteId=12345&achievement_name=First Quest Complete
    """
    try:
        # Get parameters from JSON body or query parameters
        website_id = None
        achievement_name = None
        
        if request.is_json:
            data = request.get_json()
            if data:
                website_id = data.get('websiteId')
                achievement_name = data.get('achievement_name')
        
        if not website_id:
            website_id = request.args.get('websiteId')
        if not achievement_name:
            achievement_name = request.args.get('achievement_name')
        
        if not website_id or not achievement_name:
            return jsonify({"error": "Missing required parameters: websiteId and achievement_name"}), 400
        
        # Get the achievements table manager
        achievements_manager = multi_manager.get_manager("craffft_achievements")
        if not achievements_manager:
            return jsonify({"error": "craffft_achievements table not found"}), 404
        
        # Look up the achievement by name
        achievement_row = achievements_manager.get_row("name", achievement_name)
        if not achievement_row:
            return jsonify({"error": f"Achievement '{achievement_name}' not found"}), 404
        
        # Get the students table manager
        students_manager = multi_manager.get_manager("craffft_students")
        if not students_manager:
            return jsonify({"error": "craffft_students table not found"}), 404
        
        # Verify the student exists
        student_row = students_manager.get_row("website_id", str(website_id))
        if not student_row:
            return jsonify({"error": f"Student with websiteId {website_id} not found"}), 404
        
        # Parse the achievement row to handle stringified data
        parsed_achievement = parse_database_row(achievement_row)
        
        # Get the student's current achievements
        parsed_student = parse_database_row(student_row)
        current_achievements = parsed_student.get('achievements', [])
        
        # Ensure current_achievements is a list
        if not isinstance(current_achievements, list):
            current_achievements = []
        
        # Check if achievement is already assigned
        achievement_name_to_add = parsed_achievement.get('name', achievement_name)
        if achievement_name_to_add in current_achievements:
            return jsonify({
                "message": "Achievement already assigned to student",
                "websiteId": website_id,
                "student_name": f"{student_row.get('first_name', '')} {student_row.get('last_name', '')}".strip(),
                "achievement": parsed_achievement,
                "already_assigned": True
            }), 200
        
        # Add the achievement to the student's achievements list
        updated_achievements = current_achievements + [achievement_name_to_add]
        
        # Update the student's achievements field in the database
        success = students_manager.modify_field(
            column_containing_reference="website_id",
            reference_value=str(website_id),
            target_column="achievements",
            new_value=updated_achievements
        )
        
        if not success:
            return jsonify({"error": "Failed to update student achievements in database"}), 500
        
        # Mark table as modified for Airtable sync
        multi_manager.mark_table_as_modified("craffft_students")
        
        # Return success response with the achievement data
        return jsonify({
            "message": "Achievement assigned successfully",
            "websiteId": website_id,
            "student_name": f"{student_row.get('first_name', '')} {student_row.get('last_name', '')}".strip(),
            "achievement": parsed_achievement,
            "updated_achievements": updated_achievements,
            "database_updated": True
        }), 200
        
    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500


@app.route("/sync/upload", methods=['POST'])
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



@app.route("/sync/modified-tables", methods=['GET'])
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


# Set up API documentation after all routes are defined
from docs.swagger_docs import setup_api_docs
api = setup_api_docs(app)


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