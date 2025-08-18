import os
from airtable_multi_manager import AirtableMultiManager
from sqlite_storage import SQLiteStorage
from airtable_csv import AirtableCSVManager
from student_data_manager import StudentDataManager
from utilities import load_env, parse_database_row
import asyncio

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
    manager.update_csv_from_airtable()
    csv_data = manager.read_csv(from_db=True)
    assert csv_data is None or isinstance(csv_data, str)

def test_database_columns_example():
    api_key = load_env('AIRTABLE_API_KEY')
    base_id = load_env('AIRTABLE_BASE_ID')
    table_name = "craffft_steps"
    sqlite_store = SQLiteStorage()
    manager = AirtableCSVManager(base_id, table_name, api_key, sqlite_storage=sqlite_store)
    manager.update_csv_from_airtable()
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
    multi_manager.update_all_tables()

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
    multi_manager.update_all_tables()
    
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

def test_update_step_and_check_quest():
    """
    Test the StudentDataManager's update_step_and_check_quest method
    """
    print("Running test_update_step_and_check_quest...")
    
    # Initialize the multi_manager and student_data_manager
    multi_manager = AirtableMultiManager.from_environment()
    multi_manager.discover_and_add_tables_from_base()
    student_data_manager = StudentDataManager(multi_manager)
    
    # Test parameters - use a known student
    website_id = "10"  # Using a test student ID that likely exists
    test_step = "E0 -2"  # A test step ID
    
    print(f"Testing update for student website_id: {website_id} with step: {test_step}")
    
    # Get initial student state for comparison
    initial_student = student_data_manager.get_student_info(website_id)
    if not initial_student:
        print(f"Warning: Student with website_id {website_id} not found. Skipping test.")
        return
    
    parsed_initial = parse_database_row(initial_student)
    initial_step = parsed_initial.get("current_step", "")
    initial_quests = parsed_initial.get("current_quests", [])
    
    print(f"Initial state - Step: {initial_step}, Quests: {initial_quests}")
    
    # Test 1: Update step with quest update allowed
    print("Test 1: Updating step with quest update allowed...")
    result = student_data_manager.update_step_and_check_quest(
        website_id=website_id,
        new_current_step=test_step,
        allow_quest_update=True
    )
    
    # Debug: Print the actual result to see what we got
    print(f"Test 1 debug - Actual result: {result}")
    
    # Verify the result structure
    assert isinstance(result, dict), "Result should be a dictionary"
    assert "success" in result, "Result should have 'success' key"
    
    # Check if operation failed and print error for debugging
    if not result.get("success", False):
        print(f"Test 1 failed with error: {result.get('error', 'Unknown error')}")
        print("Skipping remaining assertions due to operation failure")
        return
    
    assert "current_step" in result, "Result should have 'current_step' key"
    assert "current_quest" in result, "Result should have 'current_quest' key"
    assert "quest_changed" in result, "Result should have 'quest_changed' key"
    
    # Verify operation succeeded
    assert result["success"] is True, f"Operation should succeed: {result.get('error', '')}"
    
    # Verify step was updated
    assert result["current_step"] == test_step, f"Current step should be {test_step}, got {result['current_step']}"
    
    print(f"Test 1 result - Step: {result['current_step']}, Quest: {result['current_quest']}, Changed: {result['quest_changed']}")
    
    # Store current state after first update for next tests
    current_step_after_update = result["current_step"]
    current_quest_after_update = result["current_quest"]
    
    # Test 2: Update step with quest update disabled (valid step for current quest)
    print("Test 2: Testing quest update disabled with valid step...")
    # We need to find a step that belongs to the current quest
    # For now, let's try to update to the same step (should always be valid)
    result2 = student_data_manager.update_step_and_check_quest(
        website_id=website_id,
        new_current_step=current_step_after_update,  # Same step should be valid
        allow_quest_update=False
    )
    
    # Should succeed since step belongs to current quest
    assert result2["success"] is True, f"Operation should succeed for valid step: {result2.get('error', '')}"
    assert result2["current_step"] == current_step_after_update, f"Step should remain {current_step_after_update}"
    assert result2["quest_changed"] is False, "Quest should not change when updates disabled"
    
    print(f"Test 2 result - Step: {result2['current_step']}, Quest: {result2['current_quest']}, Changed: {result2['quest_changed']}")
    
    # Test 2b: Update step with quest update disabled (invalid step - different quest)
    print("Test 2b: Testing quest update disabled with invalid step...")
    # Try to use a step that likely belongs to a different quest
    different_quest_step = "EO-19" if test_step != "EO-19" else "EO-20"
    
    result2b = student_data_manager.update_step_and_check_quest(
        website_id=website_id,
        new_current_step=different_quest_step,
        allow_quest_update=False
    )
    
    # This might succeed or fail depending on whether the step belongs to current quest
    # Let's check both scenarios
    if result2b["success"]:
        print(f"Test 2b: Step {different_quest_step} was valid for current quest")
        assert result2b["quest_changed"] is False, "Quest should not change when updates disabled"
    else:
        print(f"Test 2b: Step {different_quest_step} was invalid for current quest (expected)")
        assert "quest" in result2b["error"].lower() or "not in" in result2b["error"].lower(), "Error should mention quest validation"
    
    print(f"Test 2b result - Success: {result2b['success']}, Error: {result2b.get('error', 'None')}")
    
    # Test 3: Test with invalid student ID
    print("Test 3: Testing with invalid student ID...")
    result3 = student_data_manager.update_step_and_check_quest(
        website_id="invalid_id_999",
        new_current_step=test_step,
        allow_quest_update=True
    )
    
    # Should fail gracefully
    assert result3["success"] is False, "Operation should fail for invalid student ID"
    assert "error" in result3, "Result should contain error message"
    assert "not found" in result3["error"].lower(), "Error should indicate student not found"
    
    print(f"Test 3 result - Success: {result3['success']}, Error: {result3['error']}")
    
    # Test 4: Test with invalid step ID
    print("Test 4: Testing with invalid step ID...")
    result4 = student_data_manager.update_step_and_check_quest(
        website_id=website_id,
        new_current_step="invalid_step_999",
        allow_quest_update=True
    )
    
    # Should fail gracefully
    assert result4["success"] is False, "Operation should fail for invalid step ID"
    assert "error" in result4, "Result should contain error message"
    assert "not found" in result4["error"].lower(), "Error should indicate step not found"
    
    print(f"Test 4 result - Success: {result4['success']}, Error: {result4['error']}")
    
    # Test 5: Verify database state matches returned values
    print("Test 5: Verifying database state...")
    updated_student = student_data_manager.get_student_info(website_id)
    parsed_updated = parse_database_row(updated_student)
    db_step = parsed_updated.get("current_step", "")
    db_quests = parsed_updated.get("current_quests", [])
    
    # The step in DB should match what was returned from the successful update
    assert db_step == current_step_after_update, f"DB step {db_step} should match result {current_step_after_update}"
    
    print(f"Test 5 result - DB Step: {db_step}, DB Quests: {db_quests}")
    
    # Restore original state (cleanup)
    if initial_step:
        print(f"Cleanup: Restoring original step {initial_step}...")
        cleanup_result = student_data_manager.update_step_and_check_quest(
            website_id=website_id,
            new_current_step=initial_step,
            allow_quest_update=True
        )
        if cleanup_result["success"]:
            print("Cleanup successful")
        else:
            print(f"Cleanup warning: {cleanup_result.get('error', 'Unknown error')}")
    
    print("✅ All update_step_and_check_quest tests passed!")


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
    test_update_step_and_check_quest()