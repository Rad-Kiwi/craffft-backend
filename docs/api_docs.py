from flask_restx import Api, Resource, fields, Namespace
from flask import request, jsonify

# Initialize the API with Swagger documentation
api = Api(
    title='Craffft Backend API',
    version='1.0',
    description='Interactive API documentation for the Craffft educational platform backend',
    doc='/docs/',
    prefix='/api'
)

# Define namespaces for organizing endpoints
students_ns = Namespace('students', description='Student management operations')
teachers_ns = Namespace('teachers', description='Teacher management operations') 
quests_ns = Namespace('quests', description='Quest and step management operations')
data_ns = Namespace('data', description='Database and table operations')
sync_ns = Namespace('sync', description='Airtable synchronization operations')

# Add namespaces to API
api.add_namespace(students_ns, path='/students')
api.add_namespace(teachers_ns, path='/teachers')
api.add_namespace(quests_ns, path='/quests')
api.add_namespace(data_ns, path='/data')
api.add_namespace(sync_ns, path='/sync')

# Define common models for request/response schemas
student_model = api.model('Student', {
    'first_name': fields.String(required=True, description='Student first name', example='John'),
    'last_name': fields.String(required=True, description='Student last name', example='Doe'),
    'gamer_tag': fields.String(required=False, description='Optional gamer tag', example='johndoe123'),
    'website_id': fields.Integer(required=True, description='Unique website identifier', example=12345),
    'current_class': fields.Integer(required=True, description='Class identifier', example=1)
})

student_response_model = api.model('StudentResponse', {
    'record_id': fields.String(description='Database record ID', example='rec1234567890'),
    'first_name': fields.String(description='Student first name', example='John'),
    'last_name': fields.String(description='Student last name', example='Doe'),
    'gamer_tag': fields.String(description='Student gamer tag', example='johndoe123'),
    'website_id': fields.Integer(description='Website ID', example=12345),
    'current_class': fields.String(description='Class assignment', example='15>1'),
    'current_quest': fields.String(description='Assigned quest', example='GG'),
    'current_step': fields.String(description='Current step', example='Step 1'),
    'quest_progress_percentage': fields.String(description='Quest progress', example='25')
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

teacher_model = api.model('Teacher', {
    'website_user_id': fields.String(required=True, description='Teacher website user ID', example='12345'),
    'first_name': fields.String(required=True, description='Teacher first name', example='Sarah'),
    'last_name': fields.String(required=True, description='Teacher last name', example='Johnson'),
    'school_name': fields.String(required=False, description='School name', example='Example Elementary')
})

teacher_response_model = api.model('TeacherResponse', {
    'record_id': fields.String(description='Database record ID'),
    'website_user_id': fields.String(description='Website user ID'),
    'first_name': fields.String(description='First name'),
    'last_name': fields.String(description='Last name'),
    'school_name': fields.String(description='School name')
})

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

# Standard response models
success_response_model = api.model('SuccessResponse', {
    'message': fields.String(description='Success message'),
    'data': fields.Raw(description='Response data')
})

error_response_model = api.model('ErrorResponse', {
    'error': fields.String(description='Error message', example='Invalid request format')
})

# Database operation models
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