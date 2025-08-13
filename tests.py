import os
from airtable_multi_manager import AirtableMultiManager
from sqlite_storage import SQLiteStorage
from airtable_csv import AirtableCSVManager
from student_data_manager import StudentDataManager
from utilities import load_env
import asyncio
from app import app

def test_basic_usage():
    multi_manager = AirtableMultiManager.from_environment()
    tables = multi_manager.get_available_tables()
    assert isinstance(tables, list)
    table_name = "DataHub_Craffft"
    csv_data = multi_manager.get_csv_data(table_name)
    if csv_data:
        assert isinstance(csv_data, str)

def test_custom_configuration():
    api_key = load_env('AIRTABLE_API_KEY')
    base_id = load_env('AIRTABLE_BASE_ID')
    table_names = ["DataHub_Craffft", "AnotherTable", "ThirdTable"]
    multi_manager = AirtableMultiManager(api_key=api_key, base_id=base_id, table_names=table_names)
    multi_manager.add_table("NewTable")
    tables = multi_manager.get_available_tables()
    assert "NewTable" in tables
    results = multi_manager.update_all_tables()
    assert isinstance(results, dict)

def test_config_dict():
    config = {
        'api_key': load_env('AIRTABLE_API_KEY'),
        'base_id': load_env('AIRTABLE_BASE_ID'),
        'table_names': ['DataHub_Craffft', 'Products', 'Customers']
    }
    multi_manager = AirtableMultiManager.from_config_dict(config)
    for table_name in multi_manager.get_available_tables():
        manager = multi_manager.get_manager(table_name)
        assert manager is not None

def test_error_handling():
    try:
        multi_manager = AirtableMultiManager.from_environment()
        result = multi_manager.get_csv_data("non-existent-table")
        assert result is None
        removed = multi_manager.remove_table("DataHub_Craffft")
        assert isinstance(removed, bool)
        result = multi_manager.get_csv_data("DataHub_Craffft")
        assert result is None
    except ValueError:
        assert True
    except Exception:
        assert True

def test_discover_tables():
    multi_manager = AirtableMultiManager.from_environment()
    table_names = multi_manager.get_tables_from_base()
    assert isinstance(table_names, list) or table_names is None
    results = multi_manager.discover_and_add_tables_from_base()
    assert isinstance(results, dict)
    if table_names:
        for table_name in table_names:
            csv_data = multi_manager.get_csv_data(table_name)
            if csv_data:
                assert isinstance(csv_data, str)

def test_update_all_tables():
    multi_manager = AirtableMultiManager.from_environment()
    table_names = multi_manager.get_tables_from_base()
    assert isinstance(table_names, list) or table_names is None
    results = multi_manager.discover_and_add_tables_from_base()
    assert isinstance(results, dict)
    if table_names:
        for table_name in table_names:
            csv_data = multi_manager.get_csv_data(table_name)
            if csv_data:
                assert isinstance(csv_data, str)
    results = multi_manager.update_all_tables()
    assert isinstance(results, dict)

def test_database_example():
    api_key = load_env('AIRTABLE_API_KEY')
    base_id = load_env('AIRTABLE_BASE_ID')
    table_name = "craffft_steps"
    sqlite_store = SQLiteStorage()
    manager = AirtableCSVManager(base_id, table_name, api_key, sqlite_storage=sqlite_store)
    manager.update_database_from_airtable()
    csv_data = manager.read_csv(from_db=True)
    assert csv_data is None or isinstance(csv_data, str)

def test_database_columns_example():
    api_key = load_env('AIRTABLE_API_KEY')
    base_id = load_env('AIRTABLE_BASE_ID')
    table_name = "craffft_steps"
    sqlite_store = SQLiteStorage()
    manager = AirtableCSVManager(base_id, table_name, api_key, sqlite_storage=sqlite_store)
    manager.update_database_from_airtable()
    column_containing_reference = "name"
    reference_value = "Garlic Hunt"
    target_column = "description"
    row = manager.get_row(column_containing_reference, reference_value)
    if row:
        assert isinstance(row, dict)
    value = manager.get_value_by_row_and_column(column_containing_reference, reference_value, target_column)
    if value:
        assert isinstance(value, str)

def test_database_value_retrieval_multi_manager():
    multi_manager = AirtableMultiManager.from_environment()
    multi_manager.discover_and_add_tables_from_base()
    column_containing_reference = "name"
    reference_value = "Garlic Hunt"
    target_column = "description"
    value = multi_manager.get_value("craffft_steps", column_containing_reference, reference_value, target_column)
    if value:
        assert isinstance(value, str)


def test_student_data_manager():
    multi_manager = AirtableMultiManager.from_environment()
    multi_manager.discover_and_add_tables_from_base()
    classroom_id = "1"
    student_data_manager = StudentDataManager(multi_manager)
    dashboard_info = student_data_manager.get_students_data_for_dashboard(classroom_id)

    print(dashboard_info)
    assert isinstance(dashboard_info, dict)
    assert 'students' in dashboard_info
    assert isinstance(dashboard_info['students'], list)
    for student in dashboard_info['students']:
        assert isinstance(student, dict)
        assert 'record_id' in student
        assert 'name' in student
        assert 'current_quest' in student
        assert 'completed_steps' in student
        assert 'progress' in student


def test_sql_query():
    multi_manager = AirtableMultiManager.from_environment()
    multi_manager.discover_and_add_tables_from_base()

    sql = "SELECT * FROM craffft_steps WHERE name = 'Garlic Hunt'"
    sql2 = "SELECT * FROM craffft_students WHERE current_class = '1'"
    results = multi_manager.execute_sql_query('craffft_steps', sql)
    results2 = multi_manager.execute_sql_query('craffft_students', sql2)
    assert isinstance(results, list)
    if results:
        assert isinstance(results[0], dict)
        assert 'name' in results[0]
        assert results[0]['name'] == 'Garlic Hunt'

    print("SQL Query Test Passed")
    print(f"Results from 'craffft_steps': {results}"
    
          f"\nResults from 'craffft_students': {results2}"
    )

def test_teacher_data():
    multi_manager = AirtableMultiManager.from_environment()
    multi_manager.discover_and_add_tables_from_base()
    website_user_id = "2"
    student_data_manager = StudentDataManager(multi_manager)
    teacher_data = student_data_manager.get_teacher_data(website_user_id)
    print(f"Teacher Data: {teacher_data}")
    assert isinstance(teacher_data, dict)
    assert 'record_id' in teacher_data
    assert 'school_name' in teacher_data

def test_update_field():
    print("Running test_update_field...")
    multi_manager = AirtableMultiManager.from_environment()
    print("Discovering and adding tables from base...")
    multi_manager.discover_and_add_tables_from_base()

    print("Getting manager for table 'craffft_steps'...")
    table_name = "craffft_steps"
    column_containing_reference = "name"
    reference_value = "Garlic Hunt"
    target_column = "description"
    new_value = "Updated description for Garlic Hunt"

    manager = multi_manager.get_manager(table_name)
    if manager:
        success = manager.modify_field(column_containing_reference, reference_value, target_column, new_value)
        assert success is True
        updated_value = manager.get_value_by_row_and_column(column_containing_reference, reference_value, target_column)
        assert updated_value == new_value
        print(f"Field '{target_column}' updated successfully for '{reference_value}' in table '{table_name}'. New value: {updated_value}")

def test_upload_to_airtable():
    """
    Test uploading modified tables back to Airtable
    """
    multi_manager = AirtableMultiManager.from_environment()
    multi_manager.discover_and_add_tables_from_base()
    
    # Modify a field in a test table
    table_name = "craffft_steps"
    column_containing_reference = "name"
    reference_value = "Garlic Hunt"
    target_column = "description" 
    new_value = "Test upload description - modified"
    
    manager = multi_manager.get_manager(table_name)
    if manager:
        # Modify the field
        success = manager.modify_field(column_containing_reference, reference_value, target_column, new_value)
        if success:
            print(f"Field modified successfully. Table {table_name} marked for upload.")
            
            # Check that the table is marked as modified
            modified_tables = multi_manager.get_modified_tables()
            assert table_name in modified_tables
            print(f"Modified tables: {modified_tables}")
            
            # Upload the modified table back to Airtable
            upload_result = multi_manager.upload_table_to_airtable(table_name)
            print(f"Upload result: {upload_result}")
            
            # Verify upload was successful
            if upload_result and not upload_result.startswith("Error"):
                print("Upload to Airtable successful!")
                
                # Check that the table is no longer marked as modified
                modified_tables_after = multi_manager.get_modified_tables()
                print(f"Modified tables after upload: {modified_tables_after}")
            else:
                print(f"Upload failed: {upload_result}")

def test_get_student_by_record_id():
    """
    Test getting a student by their record_id
    """
    multi_manager = AirtableMultiManager.from_environment()
    multi_manager.discover_and_add_tables_from_base()

    student_record = "recBc7qFYaO2797YO" 
    table_name = "craffft_students"
    
    print(f"Getting student by record_id: {student_record} from table: {table_name}")
    manager = multi_manager.get_manager(table_name)
    
    student_row = manager.get_row("record_id", student_record)
    
    assert isinstance(student_row, dict)
    assert 'record_id' in student_row
    assert student_row['record_id'] == student_record

def test_update_student_current_step_route():
    """
    Test updating a student's current_step via the API
    """
    multi_manager = AirtableMultiManager.from_environment()
    multi_manager.discover_and_add_tables_from_base()

    websiteId = "10"
    table_name = "craffft_students"

    print(f"Updating student current_step for record_id: {websiteId} in table: {table_name}")
    manager = multi_manager.get_manager(table_name)

    current_step = "EO-18"
    success = manager.modify_field("website_id", websiteId, "current_step", current_step)
    assert success is True

    # Verify the field was actually updated
    updated_row = manager.get_row("website_id", websiteId)
    assert updated_row is not None
    assert updated_row.get("current_step") == current_step
    print(f"Field verification passed: current_step = {updated_row.get('current_step')}")



    # Simulate API call
    with app.test_client() as client:
        response = client.get(f"/update-student-current-step?websiteId={websiteId}&current-step={current_step}")
        assert response.status_code == 200
        assert response.get_json().get("message") == "Student current_step updated successfully"

def run_all_tests():
    import sys
    import types
    current_module = sys.modules[__name__]
    test_functions = [getattr(current_module, name) for name in dir(current_module) if name.startswith('test_') and isinstance(getattr(current_module, name), types.FunctionType)]
    failures = 0
    for test_func in test_functions:
        try:
            test_func()
            print(f"PASS: {test_func.__name__}")
        except AssertionError:
            print(f"FAIL: {test_func.__name__}")
            failures += 1
        except Exception as e:
            print(f"ERROR: {test_func.__name__} - {e}")
            failures += 1
    if failures == 0:
        print("All tests passed.")
    else:
        print(f"{failures} test(s) failed.")

if __name__ == "__main__":
    run_all_tests()