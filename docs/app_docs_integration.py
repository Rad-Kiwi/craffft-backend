"""
API Documentation Integration for Craffft Backend

This file integrates Flask-RESTX Swagger documentation with the existing Flask app.
It creates documented versions of all endpoints while preserving the original functionality.
"""

from flask import Flask
from api_docs import api
from student_docs import students_ns
import importlib

def create_documented_app(original_app):
    """
    Create a new Flask app with API documentation that wraps the original app's functionality.
    This approach allows us to add Swagger docs without modifying the existing app structure.
    """
    
    # Initialize the API with the original app
    api.init_app(original_app)
    
    # Import the original app module to access its functions
    # We'll dynamically wrap the existing route handlers
    
    # Wrap student endpoints
    wrap_student_endpoints(original_app)
    wrap_teacher_endpoints(original_app)
    wrap_quest_endpoints(original_app)
    wrap_data_endpoints(original_app)
    wrap_sync_endpoints(original_app)
    
    return original_app

def wrap_student_endpoints(app):
    """Wrap student-related endpoints with API documentation"""
    
    # Get the original route handlers
    with app.app_context():
        # Add Students endpoint
        @students_ns.route('/add')
        class AddStudents(students_ns.resource):
            @students_ns.expect(students_ns.model('AddStudents', {
                'teacher_website_id': students_ns.fields.String(required=True, description='Teacher website ID', example='123'),
                'add_classes_to_teacher': students_ns.fields.Boolean(description='Add classes to teacher', example=True),
                'students': students_ns.fields.List(students_ns.fields.Nested(students_ns.model('Student', {
                    'first_name': students_ns.fields.String(required=True, description='First name', example='John'),
                    'last_name': students_ns.fields.String(required=True, description='Last name', example='Doe'),
                    'gamer_tag': students_ns.fields.String(description='Gamer tag', example='johndoe123'),
                    'website_id': students_ns.fields.Integer(required=True, description='Website ID', example=12345),
                    'current_class': students_ns.fields.Integer(required=True, description='Class ID', example=1)
                })), required=True)
            }))
            @students_ns.doc('add_students', description='Add multiple students to the system')
            @students_ns.response(201, 'Students added successfully')
            @students_ns.response(400, 'Invalid input')
            def post(self):
                """Add multiple students to the system"""
                # Call the original function from app.py
                from app import add_students
                return add_students()
        
        # Delete Students endpoint
        @students_ns.route('/delete')
        class DeleteStudents(students_ns.resource):
            @students_ns.expect(students_ns.model('DeleteStudents', {
                'website_ids': students_ns.fields.List(students_ns.fields.Integer, required=True, 
                                                     description='Website IDs to delete', example=[12345, 12346])
            }))
            @students_ns.doc('delete_students', description='Delete multiple students by website IDs')
            @students_ns.response(200, 'Students deleted successfully')
            @students_ns.response(404, 'Students not found')
            def delete(self):
                """Delete multiple students by their website IDs"""
                from app import delete_students
                return delete_students()
        
        # Modify Students endpoint
        @students_ns.route('/modify')
        class ModifyStudents(students_ns.resource):
            @students_ns.expect(students_ns.model('ModifyStudents', {
                'students': students_ns.fields.List(students_ns.fields.Nested(students_ns.model('ModifyStudent', {
                    'website_id': students_ns.fields.Integer(required=True, description='Website ID', example=12345),
                    'first_name': students_ns.fields.String(description='New first name', example='Jane'),
                    'last_name': students_ns.fields.String(description='New last name', example='Smith')
                })), required=True)
            }))
            @students_ns.doc('modify_students', description='Modify student names by website IDs')
            @students_ns.response(200, 'Students modified successfully')
            @students_ns.response(404, 'Students not found')
            def put(self):
                """Modify student names by their website IDs"""
                from app import modify_students
                return modify_students()

def wrap_teacher_endpoints(app):
    """Wrap teacher-related endpoints with API documentation"""
    from api_docs import teachers_ns
    
    with app.app_context():
        @teachers_ns.route('/add')
        class AddTeacher(teachers_ns.resource):
            @teachers_ns.expect(teachers_ns.model('Teacher', {
                'website_user_id': teachers_ns.fields.String(required=True, description='Website user ID', example='12345'),
                'first_name': teachers_ns.fields.String(required=True, description='First name', example='Sarah'),
                'last_name': teachers_ns.fields.String(required=True, description='Last name', example='Johnson'),
                'school_name': teachers_ns.fields.String(description='School name', example='Example Elementary')
            }))
            @teachers_ns.doc('add_teacher', description='Add a new teacher to the system')
            @teachers_ns.response(201, 'Teacher added successfully')
            @teachers_ns.response(409, 'Teacher already exists')
            def post(self):
                """Add a new teacher to the system"""
                from app import add_teacher
                return add_teacher()
        
        @teachers_ns.route('/data/<string:teacher_id>')
        class GetTeacherData(teachers_ns.resource):
            @teachers_ns.doc('get_teacher_data', description='Get teacher data by ID')
            @teachers_ns.response(200, 'Teacher data retrieved')
            @teachers_ns.response(404, 'Teacher not found')
            def get(self, teacher_id):
                """Get teacher data by ID"""
                from app import get_teacher_data
                return get_teacher_data(teacher_id)

def wrap_quest_endpoints(app):
    """Wrap quest-related endpoints with API documentation"""
    from api_docs import quests_ns
    
    with app.app_context():
        @quests_ns.route('/assign-to-class')
        class AssignQuestToClass(quests_ns.resource):
            @quests_ns.expect(quests_ns.model('ClassQuestAssignment', {
                'class_name': quests_ns.fields.String(required=True, description='Class identifier', example='15>1'),
                'quest_code': quests_ns.fields.String(required=True, description='Quest code', example='GG')
            }))
            @quests_ns.doc('assign_quest_to_class', description='Assign a quest to all students in a class')
            @quests_ns.response(200, 'Quest assigned successfully')
            @quests_ns.response(400, 'Invalid input')
            def post(self):
                """Assign a quest to all students in a given class"""
                from app import assign_quest_to_class
                return assign_quest_to_class()
        
        @quests_ns.route('/steps/data')
        class GetStepData(quests_ns.resource):
            @quests_ns.doc('get_step_data', 
                          description='Get step data from craffft_steps table',
                          params={'step': 'Specific step name (optional)'})
            @quests_ns.response(200, 'Step data retrieved')
            @quests_ns.response(404, 'Step not found')
            def get(self):
                """Get step data - all steps or specific step by name"""
                from app import get_step_data
                return get_step_data()
        
        @quests_ns.route('/achievements/assign')
        class AssignAchievement(quests_ns.resource):
            @quests_ns.expect(quests_ns.model('AchievementAssignment', {
                'websiteId': quests_ns.fields.Integer(required=True, description='Student website ID', example=12345),
                'achievement_name': quests_ns.fields.String(required=True, description='Achievement name', example='First Quest Complete')
            }))
            @quests_ns.doc('assign_achievement', description='Assign an achievement to a student')
            @quests_ns.response(200, 'Achievement assigned successfully')
            @quests_ns.response(404, 'Student or achievement not found')
            def post(self):
                """Assign an achievement to a student"""
                from app import assign_achievement_to_student
                return assign_achievement_to_student()

def wrap_data_endpoints(app):
    """Wrap data-related endpoints with API documentation"""
    from api_docs import data_ns
    
    with app.app_context():
        @data_ns.route('/table/csv/<string:table_name>')
        class GetTableCSV(data_ns.resource):
            @data_ns.doc('get_table_csv', description='Get table data as CSV')
            @data_ns.response(200, 'CSV data retrieved')
            @data_ns.response(404, 'Table not found')
            def get(self, table_name):
                """Get all data from a table as CSV"""
                from app import get_table_manager
                return get_table_manager(table_name)
        
        @data_ns.route('/table/json/<string:table_name>')
        class GetTableJSON(data_ns.resource):
            @data_ns.doc('get_table_json', description='Get table data as JSON')
            @data_ns.response(200, 'JSON data retrieved')
            @data_ns.response(404, 'Table not found')
            def get(self, table_name):
                """Get all data from a table as JSON"""
                from app import get_tile_data
                return get_tile_data(table_name)
        
        @data_ns.route('/field/modify')
        class ModifyField(data_ns.resource):
            @data_ns.expect(data_ns.model('FieldUpdate', {
                'table_name': data_ns.fields.String(required=True, description='Table name', example='craffft_students'),
                'reference_value': data_ns.fields.String(required=True, description='Reference value', example='12345'),
                'target_column': data_ns.fields.String(required=True, description='Column to update', example='first_name'),
                'new_value': data_ns.fields.Raw(required=True, description='New value', example='John'),
                'column_containing_reference': data_ns.fields.String(description='Reference column', example='website_id', default='id')
            }))
            @data_ns.doc('modify_field', description='Update a specific field in a table')
            @data_ns.response(200, 'Field updated successfully')
            @data_ns.response(404, 'Record not found')
            def post(self):
                """Update a specific field in a database table"""
                from app import update_field
                return update_field()

def wrap_sync_endpoints(app):
    """Wrap Airtable sync endpoints with API documentation"""
    from api_docs import sync_ns
    
    with app.app_context():
        @sync_ns.route('/from-airtable/all')
        class UpdateFromAirtableAll(sync_ns.resource):
            @sync_ns.doc('update_from_airtable_all', description='Update all tables from Airtable')
            @sync_ns.response(200, 'Tables updated successfully')
            @sync_ns.response(500, 'Update failed')
            def post(self):
                """Update all tables from Airtable"""
                from app import update_server_from_airtable
                return update_server_from_airtable()
        
        @sync_ns.route('/from-airtable/table')
        class UpdateFromAirtableTable(sync_ns.resource):
            @sync_ns.expect(sync_ns.model('TableUpdate', {
                'table_name': sync_ns.fields.String(required=True, description='Table name', example='craffft_students'),
                'force_delete': sync_ns.fields.Boolean(description='Force delete and recreate', example=True, default=True)
            }))
            @sync_ns.doc('update_from_airtable_table', description='Update specific table from Airtable')
            @sync_ns.response(200, 'Table updated successfully')
            @sync_ns.response(404, 'Table not found')
            def post(self):
                """Update specific table from Airtable"""
                from app import update_table_from_airtable
                return update_table_from_airtable()
        
        @sync_ns.route('/to-airtable')
        class UploadToAirtable(sync_ns.resource):
            @sync_ns.doc('upload_to_airtable', 
                        description='Upload modified tables to Airtable',
                        params={
                            'force_upload': 'Force upload all tables (optional)',
                            'table_name': 'Specific table to upload (optional)'
                        })
            @sync_ns.response(200, 'Upload successful')
            @sync_ns.response(500, 'Upload failed')
            def post(self):
                """Upload all modified tables back to Airtable"""
                from app import upload_to_airtable
                return upload_to_airtable()
        
        @sync_ns.route('/modified-tables')
        class GetModifiedTables(sync_ns.resource):
            @sync_ns.doc('get_modified_tables', description='Get list of tables that need to be uploaded')
            @sync_ns.response(200, 'Modified tables retrieved')
            def get(self):
                """Get a list of tables that have been modified"""
                from app import get_modified_tables
                return get_modified_tables()