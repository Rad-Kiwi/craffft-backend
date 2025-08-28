#!/usr/bin/env python3
"""
Test script for quest completion functionality
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from airtable_multi_manager import AirtableMultiManager
from student_data_manager import StudentDataManager
from utilities import parse_database_row

def test_quest_completion():
    """Test quest completion logic when a student reaches 100% progress"""
    print("Testing quest completion functionality...")
    
    # Initialize managers
    multi_manager = AirtableMultiManager.from_environment()
    multi_manager.discover_and_add_tables_from_base()
    student_data_manager = StudentDataManager(multi_manager)
    
    # Test parameters
    website_id = "10"  # Using a test student
    
    print(f"Testing quest completion for student website_id: {website_id}")
    
    # Get initial student state
    initial_student = student_data_manager.get_student_info(website_id)
    if not initial_student:
        print(f"Error: Student with website_id {website_id} not found")
        return
    
    parsed_initial = parse_database_row(initial_student)
    initial_step = parsed_initial.get("current_step", "")
    initial_quest = parsed_initial.get("current_quest", "")
    initial_completed_quests = parsed_initial.get("completed_quests", [])
    initial_progress = parsed_initial.get("quest_progress_percentage", 0)
    
    print(f"Initial state:")
    print(f"  Step: {initial_step}")
    print(f"  Quest: {initial_quest}")
    print(f"  Completed quests: {initial_completed_quests}")
    print(f"  Progress: {initial_progress}%")
    
    # Find a step that might complete the quest (try multiple test steps)
    test_steps = ["WW-3", "WW-4", "WW-5", "EO-19", "EO-20", "EO-21"]
    
    for test_step in test_steps:
        print(f"\nTesting step: {test_step}")
        
        # Test updating to this step
        result = student_data_manager.update_step_and_check_quest(
            website_id=website_id,
            new_current_step=test_step,
            allow_quest_update=True
        )
        
        if result["success"]:
            print(f"Update successful:")
            print(f"  Current step: {result['current_step']}")
            print(f"  Current quest: {result['current_quest']}")
            print(f"  Quest changed: {result['quest_changed']}")
            print(f"  Quest completed: {result.get('quest_completed', False)}")
            
            # Get updated student info to check database state
            updated_student = student_data_manager.get_student_info(website_id)
            parsed_updated = parse_database_row(updated_student)
            db_quest = parsed_updated.get("current_quest", "")
            db_completed_quests = parsed_updated.get("completed_quests", [])
            db_progress = float(parsed_updated.get("quest_progress_percentage", 0))
            
            print(f"  Database state:")
            print(f"    Current quest: '{db_quest}'")
            print(f"    Completed quests: {db_completed_quests}")
            print(f"    Progress: {db_progress}%")
            
            # Check if quest was completed
            if result.get('quest_completed', False):
                print(f"🎉 QUEST COMPLETION DETECTED!")
                print(f"  Quest '{initial_quest}' should be in completed_quests")
                print(f"  Current quest should be empty/null")
                
                # Verify completion was handled correctly
                if db_quest == "":
                    print("  ✅ Current quest correctly set to empty")
                else:
                    print(f"  ❌ Current quest should be empty, but is: '{db_quest}'")
                
                if initial_quest in db_completed_quests:
                    print("  ✅ Completed quest correctly added to completed_quests")
                else:
                    print(f"  ❌ Quest '{initial_quest}' not found in completed_quests: {db_completed_quests}")
                
                break  # Found a completion, exit loop
                
            # If progress reached 100% but quest wasn't marked complete, investigate
            if db_progress >= 100.0:
                print(f"  Progress is {db_progress}% but quest_completed is {result.get('quest_completed', False)}")
        
        else:
            print(f"  Update failed: {result.get('error', 'Unknown error')}")
    
    # Restore original state (cleanup)
    if initial_step:
        print(f"\nCleanup: Restoring original state...")
        cleanup_result = student_data_manager.update_step_and_check_quest(
            website_id=website_id,
            new_current_step=initial_step,
            allow_quest_update=True
        )
        if cleanup_result["success"]:
            # Also restore the quest if needed
            if initial_quest and cleanup_result["current_quest"] != initial_quest:
                student_manager = multi_manager.get_manager("craffft_students")
                student_manager.modify_field("website_id", website_id, "current_quest", initial_quest)
                student_manager.modify_field("website_id", website_id, "completed_quests", initial_completed_quests)
            print("  ✅ Cleanup successful")
        else:
            print(f"  ❌ Cleanup failed: {cleanup_result.get('error', 'Unknown error')}")

if __name__ == "__main__":
    test_quest_completion()
