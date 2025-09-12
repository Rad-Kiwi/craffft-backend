"""
Interactive API Documentation for Craffft Backend

This file adds Flask-RESTX Swagger documentation to your existing Flask app.
It creates a documented API interface while preserving all existing functionality.

Usage:
1. Import this module in your app.py
2. Call setup_api_docs(app) after creating your Flask app
3. Access documentation at /docs/
"""

from flask_restx import Api, Resource, fields, Namespace
from flask import request, jsonify

def setup_api_docs(app):
    """
    Set up API documentation for the Flask app
    """
    
    # Helper function to call view functions properly
    def call_view_function(func_name, *args, **kwargs):
        from flask import current_app
        from flask.wrappers import Response
        import json
        
        view_func = current_app.view_functions[func_name]
        result = view_func(*args, **kwargs)
        
        # Handle tuple responses (response, status_code)
        if isinstance(result, tuple):
            response_obj = result[0]
            status_code = result[1] if len(result) > 1 else 200
            
            # If it's a Flask Response object, extract the data
            if isinstance(response_obj, Response):
                # Check if it's JSON content
                if response_obj.content_type and 'application/json' in response_obj.content_type:
                    try:
                        # Parse the JSON data from the response
                        data = json.loads(response_obj.get_data(as_text=True))
                        return data, status_code
                    except (json.JSONDecodeError, ValueError):
                        # If JSON parsing fails, return the raw text
                        return {"data": response_obj.get_data(as_text=True)}, status_code
                else:
                    # For non-JSON responses (like CSV), return as text
                    return {"data": response_obj.get_data(as_text=True), "content_type": response_obj.content_type}, status_code
            else:
                # If it's already data, return as is
                return result
        
        # If it's a single Flask Response object, extract the data
        elif isinstance(result, Response):
            # Check if it's JSON content
            if result.content_type and 'application/json' in result.content_type:
                try:
                    # Parse the JSON data from the response
                    return json.loads(result.get_data(as_text=True))
                except (json.JSONDecodeError, ValueError):
                    # If JSON parsing fails, return the raw text
                    return {"data": result.get_data(as_text=True)}
            else:
                # For non-JSON responses (like CSV), return as text
                return {"data": result.get_data(as_text=True), "content_type": result.content_type}
        
        # If it's already raw data, return as is
        return result
    
    # Initialize the API with Swagger documentation
    api = Api(
        app,
        title='Craffft Backend API',
        version='1.0',
        description="""
        Interactive API documentation for the Craffft educational platform backend.
        
        ## Features
        - Student management (add, delete, modify, retrieve)
        - Teacher management 
        - Quest and step tracking
        - Achievement assignment
        - Airtable synchronization
        - Database operations
        
        ## Authentication
        No authentication required for most endpoints.
        
        ## Rate Limiting
        No rate limiting currently implemented.
        
        ## Base URL
        All endpoints are relative to the base URL of this server.
        """,
        doc='/docs/',
        prefix=''  # No prefix to match existing routes
    )
    
    # Define namespaces for organizing endpoints
    students_ns = Namespace('Students', description='Student management operations')
    teachers_ns = Namespace('Teachers', description='Teacher management operations') 
    quests_ns = Namespace('Quests & Steps', description='Quest and step management operations')
    data_ns = Namespace('Database', description='Database and table operations')
    sync_ns = Namespace('Airtable Sync', description='Airtable synchronization operations')
    
    # Add namespaces to API
    api.add_namespace(students_ns)
    api.add_namespace(teachers_ns)
    api.add_namespace(quests_ns)
    api.add_namespace(data_ns)
    api.add_namespace(sync_ns)
    
    # Define data models for request/response schemas
    
    # Student models
    student_model = api.model('Student', {
        'first_name': fields.String(required=True, description='Student first name', example='John'),
        'last_name': fields.String(required=True, description='Student last name', example='Doe'),
        'gamer_tag': fields.String(required=False, description='Optional gamer tag', example='johndoe123'),
        'website_id': fields.Integer(required=True, description='Unique website identifier', example=12345),
        'current_class': fields.Integer(required=True, description='Class identifier', example=1)
    })
    
    add_students_model = api.model('AddStudents', {
        'teacher_website_id': fields.String(required=True, description='Teacher website ID', example='123'),
        'add_classes_to_teacher': fields.Boolean(description='Whether to add classes to teacher', example=True),
        'students': fields.List(fields.Nested(student_model), required=True, description='List of students to add')
    })
    
    delete_students_model = api.model('DeleteStudents', {
        'website_ids': fields.List(fields.Integer, required=True, description='List of website IDs to delete', example=[12345, 12346])
    })
    
    modify_student_model = api.model('ModifyStudent', {
        'website_id': fields.Integer(required=True, description='Student website ID', example=12345),
        'first_name': fields.String(required=False, description='New first name', example='Jane'),
        'last_name': fields.String(required=False, description='New last name', example='Smith')
    })
    
    modify_students_model = api.model('ModifyStudents', {
        'students': fields.List(fields.Nested(modify_student_model), required=True, description='List of student modifications')
    })
    
    # Teacher models
    teacher_model = api.model('Teacher', {
        'website_user_id': fields.String(required=True, description='Teacher website user ID', example='12345'),
        'first_name': fields.String(required=True, description='Teacher first name', example='Sarah'),
        'last_name': fields.String(required=True, description='Teacher last name', example='Johnson'),
        'school_name': fields.String(required=False, description='School name', example='Example Elementary')
    })
    
    # Quest models
    quest_assignment_model = api.model('QuestAssignment', {
        'websiteId': fields.Integer(required=True, description='Student website ID', example=12345),
        'quest_code': fields.String(required=True, description='Quest code to assign', example='GG')
    })
    
    quest_assignments_model = api.model('QuestAssignments', {
        'assignments': fields.List(fields.Nested(quest_assignment_model), required=True, description='List of quest assignments')
    })
    
    class_quest_assignment_model = api.model('ClassQuestAssignment', {
        'class_name': fields.String(required=True, description='Class identifier', example='15>1'),
        'quest_code': fields.String(required=True, description='Quest code to assign', example='GG')
    })
    
    achievement_assignment_model = api.model('AchievementAssignment', {
        'websiteId': fields.Integer(required=True, description='Student website ID', example=12345),
        'achievement_name': fields.String(required=True, description='Achievement name', example='First Quest Complete')
    })
    
    # Database models
    table_update_model = api.model('TableUpdate', {
        'table_name': fields.String(required=True, description='Table name to update', example='craffft_students'),
        'force_delete': fields.Boolean(description='Force delete and recreate table', example=True)
    })
    
    field_update_model = api.model('FieldUpdate', {
        'table_name': fields.String(required=True, description='Table name', example='craffft_students'),
        'reference_value': fields.String(required=True, description='Reference value to find record', example='12345'),
        'target_column': fields.String(required=True, description='Column to update', example='first_name'),
        'new_value': fields.Raw(required=True, description='New value for the field', example='John'),
        'column_containing_reference': fields.String(description='Column containing reference value', example='website_id', default='id')
    })
    
    db_query_model = api.model('DatabaseQuery', {
        'table_name': fields.String(required=True, description='Table name to query', example='craffft_students'),
        'reference_value': fields.String(required=True, description='Reference value to find', example='12345'),
        'target_column': fields.String(description='Specific column to retrieve (optional)', example='first_name'),
        'column_containing_reference': fields.String(description='Column containing reference value', example='website_id', default='id')
    })
    
    # Standard response models
    success_response_model = api.model('SuccessResponse', {
        'message': fields.String(description='Success message'),
        'data': fields.Raw(description='Response data')
    })
    
    error_response_model = api.model('ErrorResponse', {
        'error': fields.String(description='Error message', example='Invalid request format')
    })
    
    # Now create the documented endpoints that wrap the existing functionality
    # We'll use a decorator approach to avoid duplicating route logic
    
    # =============================================================================
    # STUDENT ENDPOINTS
    # =============================================================================
    
    @students_ns.route('/add-students')
    class AddStudentsDoc(Resource):
        @students_ns.expect(add_students_model, validate=True)
        @students_ns.doc('add_students', 
                        description="""
                        Add multiple students to the system.
                        
                        **Requirements:**
                        - All students must have unique website_ids
                        - Teacher website_id must exist if add_classes_to_teacher is true
                        - gamer_tag is optional but recommended
                        
                        **Behavior:**
                        - Students are added to the craffft_students table
                        - Class format: "teacher_website_id>class_number"
                        - Automatically marks table for Airtable sync
                        """)
        @students_ns.response(201, 'Students added successfully', success_response_model)
        @students_ns.response(400, 'Invalid input or missing required fields', error_response_model)
        @students_ns.response(500, 'Internal server error', error_response_model)
        def post(self):
            """Add multiple students to the system"""
            # Get the app module that's already loaded
            return call_view_function('add_students')
    
    @students_ns.route('/delete-students')
    class DeleteStudentsDoc(Resource):
        @students_ns.expect(delete_students_model, validate=True)
        @students_ns.doc('delete_students',
                        description="""
                        Delete multiple students by their website IDs.
                        
                        **Behavior:**
                        - Removes students from craffft_students table
                        - Returns details of successful and failed deletions
                        - Automatically marks table for Airtable sync
                        """)
        @students_ns.response(200, 'All students deleted successfully', success_response_model)
        @students_ns.response(404, 'Some or all students not found', error_response_model)
        @students_ns.response(207, 'Partial success - some deletions failed', success_response_model)
        @students_ns.response(422, 'Delete operation failed', error_response_model)
        def delete(self):
            """Delete multiple students by their website IDs"""
            return call_view_function('delete_students')
    
    @students_ns.route('/modify-students')
    class ModifyStudentsDoc(Resource):
        @students_ns.expect(modify_students_model, validate=True)
        @students_ns.doc('modify_students',
                        description="""
                        Modify student names by their website IDs.
                        
                        **Features:**
                        - Can update first_name, last_name, or both
                        - Only provided fields will be updated
                        - Returns details of successful and failed modifications
                        """)
        @students_ns.response(200, 'All students modified successfully', success_response_model)
        @students_ns.response(404, 'Some or all students not found', error_response_model)
        @students_ns.response(207, 'Partial success - some modifications failed', success_response_model)
        @students_ns.response(422, 'Modification operation failed', error_response_model)
        def put(self):
            """Modify student names by their website IDs"""
            return call_view_function('modify_students')
    
    @students_ns.route('/get-student-data-from-websiteId/<int:website_id>')
    class GetStudentByWebsiteIdDoc(Resource):
        @students_ns.doc('get_student_by_website_id',
                        description="""
                        Retrieve student data by website ID.
                        
                        **Returns:**
                        - Complete student record with parsed JSON fields
                        - Current quest and step information
                        - Achievement history
                        """)
        @students_ns.response(200, 'Student found', success_response_model)
        @students_ns.response(404, 'Student not found', error_response_model)
        def get(self, website_id):
            """Get student data by website ID"""
            return call_view_function('get_student_data_from_website', website_id)
    
    @students_ns.route('/get-student-data-from-record/<string:student_record>')
    class GetStudentByRecordDoc(Resource):
        @students_ns.doc('get_student_by_record',
                        description="Retrieve student data by record ID")
        @students_ns.response(200, 'Student found', success_response_model)
        @students_ns.response(404, 'Student not found', error_response_model)
        def get(self, student_record):
            """Get student data by record ID"""
            return call_view_function('get_student_data', student_record)
    
    @students_ns.route('/get-student-data-dashboard/<string:classroom_id>')
    class GetStudentsDashboardDoc(Resource):
        @students_ns.doc('get_students_dashboard',
                        description="""
                        Get comprehensive student data for dashboard display.
                        
                        **Features:**
                        - Returns all students in the specified classroom
                        - Includes progress tracking and quest information
                        - Formatted for dashboard consumption
                        """)
        @students_ns.response(200, 'Dashboard data retrieved', success_response_model)
        @students_ns.response(404, 'Classroom not found', error_response_model)
        def get(self, classroom_id):
            """Get student data for dashboard by classroom ID"""
            return call_view_function('get_students_for_dashboard', classroom_id)
    
    @students_ns.route('/update-student-current-step')
    class UpdateStudentCurrentStepDoc(Resource):
        @students_ns.doc('update_student_current_step',
                        description="Update a student's current step",
                        params={
                            'websiteId': {'description': 'Student website ID', 'required': True, 'type': 'string'},
                            'current-step': {'description': 'New current step', 'required': True, 'type': 'string'}
                        })
        @students_ns.response(200, 'Current step updated successfully', success_response_model)
        @students_ns.response(400, 'Missing required parameters', error_response_model)
        @students_ns.response(404, 'Student not found', error_response_model)
        def get(self):
            """Update student's current step"""
            return call_view_function('update_student_current_step')
    
    @students_ns.route('/update-and-check-quest')
    class UpdateAndCheckQuestDoc(Resource):
        @students_ns.doc('update_and_check_quest',
                        description="""
                        Update student's current step and check if quest changed.
                        
                        **Logic:**
                        - Updates the student's current step
                        - Checks if quest should advance based on step progress
                        - Returns quest change status
                        """,
                        params={
                            'websiteId': {'description': 'Student website ID', 'required': True, 'type': 'string'},
                            'current-step': {'description': 'New current step', 'required': True, 'type': 'string'},
                            'allow-quest-update': {'description': 'Allow quest update', 'required': False, 'type': 'boolean', 'default': True}
                        })
        @students_ns.response(200, 'Step and quest updated successfully', success_response_model)
        @students_ns.response(400, 'Invalid request parameters', error_response_model)
        def get(self):
            """Update student's current step and check if quest changed"""
            return call_view_function('update_and_check_quest')
    
    # =============================================================================
    # TEACHER ENDPOINTS
    # =============================================================================
    
    @teachers_ns.route('/add-teacher')
    class AddTeacherDoc(Resource):
        @teachers_ns.expect(teacher_model, validate=True)
        @teachers_ns.doc('add_teacher',
                        description="""
                        Add a new teacher to the system.
                        
                        **Requirements:**
                        - website_user_id must be unique
                        - first_name and last_name are required
                        - school_name is optional
                        """)
        @teachers_ns.response(201, 'Teacher added successfully', success_response_model)
        @teachers_ns.response(400, 'Missing required fields', error_response_model)
        @teachers_ns.response(409, 'Teacher already exists', error_response_model)
        @teachers_ns.response(500, 'Internal server error', error_response_model)
        def post(self):
            """Add a new teacher to the system"""
            return call_view_function('add_teacher')
    
    @teachers_ns.route('/get-teacher-data/<string:teacher_id>')
    class GetTeacherDataDoc(Resource):
        @teachers_ns.doc('get_teacher_data',
                        description="Retrieve teacher data and associated class information")
        @teachers_ns.response(200, 'Teacher data retrieved', success_response_model)
        @teachers_ns.response(404, 'Teacher not found', error_response_model)
        def get(self, teacher_id):
            """Get teacher data by ID"""
            return call_view_function('get_teacher_data', teacher_id)
    
    # =============================================================================
    # QUEST & ACHIEVEMENT ENDPOINTS
    # =============================================================================
    
    @quests_ns.route('/assign-quests')
    class AssignQuestsDoc(Resource):
        @quests_ns.expect(quest_assignments_model, validate=True)
        @quests_ns.doc('assign_quests',
                      description="""
                      Assign quests to multiple students.
                      
                      **Features:**
                      - Batch assignment of different quests to different students
                      - Returns success/failure status for each assignment
                      """)
        @quests_ns.response(200, 'Quests assigned successfully', success_response_model)
        @quests_ns.response(400, 'Invalid input format', error_response_model)
        def post(self):
            """Assign quests to multiple students"""
            return call_view_function('assign_quests')
    
    @quests_ns.route('/assign-quest-to-class')
    class AssignQuestToClassDoc(Resource):
        @quests_ns.expect(class_quest_assignment_model, validate=True)
        @quests_ns.doc('assign_quest_to_class',
                      description="""
                      Assign a quest to all students in a given class.
                      
                      **Features:**
                      - Assigns the same quest to all students in a class
                      - Resets quest progress for students
                      - Can also be called with query parameters
                      """)
        @quests_ns.response(200, 'Quest assigned to class successfully', success_response_model)
        @quests_ns.response(400, 'Missing required parameters', error_response_model)
        def post(self):
            """Assign a quest to all students in a given class"""
            return call_view_function('assign_quest_to_class')
    
    @quests_ns.route('/get-step-data')
    class GetStepDataDoc(Resource):
        @quests_ns.doc('get_step_data',
                      description="""
                      Get step data from craffft_steps table.
                      
                      **Options:**
                      - No parameters: Returns all steps
                      - step parameter: Returns specific step by name
                      """,
                      params={'step': {'description': 'Specific step name (optional)', 'type': 'string'}})
        @quests_ns.response(200, 'Step data retrieved', success_response_model)
        @quests_ns.response(404, 'Step not found', error_response_model)
        def get(self):
            """Get step data - all steps or specific step by name"""
            return call_view_function('get_step_data')
    
    @quests_ns.route('/assign-achievement-to-student')
    class AssignAchievementDoc(Resource):
        @quests_ns.expect(achievement_assignment_model, validate=True)
        @quests_ns.doc('assign_achievement',
                      description="""
                      Assign an achievement to a student.
                      
                      **Features:**
                      - Adds achievement to student's achievement list
                      - Prevents duplicate achievements
                      - Can also be called with query parameters
                      """)
        @quests_ns.response(200, 'Achievement assigned successfully', success_response_model)
        @quests_ns.response(404, 'Student or achievement not found', error_response_model)
        def post(self):
            """Assign an achievement to a student"""
            return call_view_function('assign_achievement_to_student')
    
    # =============================================================================
    # DATABASE ENDPOINTS
    # =============================================================================
    
    @data_ns.route('/get-table-as-csv/<string:table_name>')
    class GetTableCSVDoc(Resource):
        @data_ns.doc('get_table_csv',
                    description="Get all data from a table as CSV format")
        @data_ns.response(200, 'CSV data retrieved')
        @data_ns.response(404, 'Table not found')
        def get(self, table_name):
            """Get all data from a table as CSV"""
            return call_view_function('get_table_manager', table_name)
    
    @data_ns.route('/get-table-as-json/<string:table_name>')
    class GetTableJSONDoc(Resource):
        @data_ns.doc('get_table_json',
                    description="""
                    Get all data from a table as JSON.
                    
                    **Features:**
                    - Returns parsed JSON data with proper data types
                    - Handles stringified lists and objects
                    """)
        @data_ns.response(200, 'JSON data retrieved')
        @data_ns.response(404, 'Table not found')
        def get(self, table_name):
            """Get all data from a table as JSON"""
            return call_view_function('get_tile_data', table_name)
    
    @data_ns.route('/get-value-from-db')
    class GetValueFromDBDoc(Resource):
        @data_ns.expect(db_query_model, validate=True)
        @data_ns.doc('get_value_from_db',
                    description="""
                    Query database for specific values or records.
                    
                    **Options:**
                    - With target_column: Returns specific field value
                    - Without target_column: Returns entire record
                    """)
        @data_ns.response(200, 'Data retrieved successfully')
        @data_ns.response(404, 'Record not found')
        def post(self):
            """Query database for specific values or records"""
            return call_view_function('get_value_from_db')
    
    @data_ns.route('/modify-field')
    class ModifyFieldDoc(Resource):
        @data_ns.expect(field_update_model, validate=True)
        @data_ns.doc('modify_field',
                    description="""
                    Update a specific field in a database table.
                    
                    **Features:**
                    - Flexible field updates in any table
                    - Customizable reference column
                    - Supports any data type for new_value
                    """)
        @data_ns.response(200, 'Field updated successfully')
        @data_ns.response(404, 'Record not found')
        @data_ns.response(500, 'Update failed')
        def post(self):
            """Update a specific field in a database table"""
            return call_view_function('update_field')
    
    # =============================================================================
    # AIRTABLE SYNC ENDPOINTS
    # =============================================================================
    
    @sync_ns.route('/update-server-from-airtable')
    class UpdateFromAirtableAllDoc(Resource):
        @sync_ns.doc('update_from_airtable_all',
                    description="""
                    Update all tables from Airtable.
                    
                    **Behavior:**
                    - Downloads latest data from all Airtable tables
                    - Overwrites local database tables
                    - Returns update status for each table
                    """)
        @sync_ns.response(200, 'All tables updated successfully')
        @sync_ns.response(500, 'Some or all updates failed')
        def post(self):
            """Update all tables from Airtable"""
            return call_view_function('update_server_from_airtable')
    
    @sync_ns.route('/update-table-from-airtable')
    class UpdateFromAirtableTableDoc(Resource):
        @sync_ns.expect(table_update_model, validate=True)
        @sync_ns.doc('update_from_airtable_table',
                    description="""
                    Update specific table from Airtable.
                    
                    **Options:**
                    - force_delete: Whether to delete and recreate table (default: true)
                    - Can also use query parameters instead of JSON body
                    """)
        @sync_ns.response(200, 'Table updated successfully')
        @sync_ns.response(404, 'Table not found')
        @sync_ns.response(500, 'Update failed')
        def post(self):
            """Update specific table from Airtable"""
            return call_view_function('update_table_from_airtable')
    
    @sync_ns.route('/upload-to-airtable')
    class UploadToAirtableDoc(Resource):
        @sync_ns.doc('upload_to_airtable',
                    description="""
                    Upload modified tables back to Airtable.
                    
                    **Query Parameters:**
                    - force_upload: Upload all tables regardless of modification status
                    - table_name: Upload specific table only
                    """,
                    params={
                        'force_upload': {'description': 'Force upload all tables', 'type': 'boolean'},
                        'table_name': {'description': 'Specific table to upload', 'type': 'string'}
                    })
        @sync_ns.response(200, 'Upload successful')
        @sync_ns.response(207, 'Partial success - some uploads failed')
        @sync_ns.response(500, 'Upload failed')
        def post(self):
            """Upload all modified tables back to Airtable"""
            return call_view_function('upload_to_airtable')
    
    @sync_ns.route('/get-modified-tables')
    class GetModifiedTablesDoc(Resource):
        @sync_ns.doc('get_modified_tables',
                    description="Get list of tables that have been modified and need to be uploaded")
        @sync_ns.response(200, 'Modified tables list retrieved')
        def get(self):
            """Get a list of tables that have been modified"""
            return call_view_function('get_modified_tables')
    
    return api