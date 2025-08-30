from utilities import parse_database_row, process_quest_data_for_frontend
import json
class StudentDataManager:
    def __init__(self, airtable_multi_manager):
        if airtable_multi_manager is None:
            raise ValueError("airtable_multi_manager cannot be None")
        self.airtable_multi_manager = airtable_multi_manager

    @staticmethod
    def get_steps_sql(field_name, query_data):
        ids_str = "', '".join(query_data)
        sql = f"SELECT * FROM craffft_steps WHERE {field_name} IN ('{ids_str}')"
        return sql

    @staticmethod
    def get_step_data_by_key(key, data, key_field):
        """
        Safely get a step data dict from a list of dicts by key.
        """
        if not data or not isinstance(data, list):
            return None
        for item in data:
            if item.get(key_field) == key:
                return item
        return None

    @staticmethod
    def get_progress(student, current_quest_obj):
        """
        Calculate the progress percentage for a student on their current quest.
        Uses the student's current_step position in the ordered quest steps list.
        Returns a string formatted to two decimal places.
        """
        if not current_quest_obj or 'steps' not in current_quest_obj:
            print('Missing quest object or steps')
            return "0.00"
        
        # Parse the student data to get current_step
        parsed_student = parse_database_row(student)
        current_step = parsed_student.get('current_step', '')
        
        # Parse the quest object to get the ordered steps list
        parsed_quest = parse_database_row(current_quest_obj)
        quest_steps = parsed_quest.get('steps', [])
        
        # Ensure we have a list to work with
        if not isinstance(quest_steps, list) or not quest_steps:
            print('Quest steps is not a valid list')
            return "0.00"
        
        # If student has no current step, progress is 0
        if not current_step:
            return "0.00"
        
        try:
            # Find the index of the current step in the ordered quest steps
            current_step_index = quest_steps.index(current_step)
            # Progress is based on steps completed (index + 1) vs total steps
            progress_percentage = ((current_step_index + 1) / len(quest_steps)) * 100
            return "{:.2f}".format(progress_percentage)
        except ValueError:
            # Current step not found in quest steps - student might be on wrong quest or step doesn't exist
            print(f'Current step "{current_step}" not found in quest steps: {quest_steps}')
            return "0.00"
        except Exception as e:
            print(f'Error calculating progress: {e}')
            return "0.00"

    def get_students_data_for_dashboard(self, classroom_id):
        # Retrieve the students for the classroom
        students = self.get_student_by_class(classroom_id)

        # Collect unique quest IDs from students
        unique_quests = []
        for student in students:
            parsed_student = parse_database_row(student)
            current_quest = parsed_student.get('current_quest', '')
            if current_quest and current_quest not in unique_quests:
                unique_quests.append(current_quest)

        # Get quest data for the unique quests if any exist
        quest_data = []
        if unique_quests:
            ids_str = "', '".join(unique_quests)
            sql = f"SELECT * FROM craffft_quests WHERE short_code IN ('{ids_str}')"
            raw_quest_data = self.airtable_multi_manager.execute_sql_query('craffft_quests', sql) or []
            
            # Process quest data for frontend consumption
            quest_data = process_quest_data_for_frontend(raw_quest_data)

        # Process each student to add quest details
        for student in students:
            parsed_student = parse_database_row(student)
            current_quest_id = parsed_student.get('current_quest', '')
            current_step = parsed_student.get('current_step', '')
            
            # Use stored progress percentage directly
            student['progress'] = parsed_student.get('quest_progress_percentage', '0.00')
            
            # Find and add current quest details
            current_quest_obj = None
            if current_quest_id:
                current_quest_obj = next((obj for obj in quest_data if obj.get('record_id') == current_quest_id), None)
            
            if current_quest_obj:
                student['current_quest_name'] = current_quest_obj.get('quest_name', '')
                student['current_quest_description'] = current_quest_obj.get('quest_description', '')
                
                # Get current step data if we have a current step
                student['current_step_data'] = None
                if current_step:
                    step_manager = self.airtable_multi_manager.get_manager("craffft_steps")
                    if step_manager:
                        student['current_step_data'] = step_manager.get_row("record_id", current_step)
                
                # For completed steps, we can calculate them based on current step position
                parsed_quest = parse_database_row(current_quest_obj)
                quest_steps = parsed_quest.get('steps', [])
                current_quest_completed_steps_info = []
                
                if current_step and isinstance(quest_steps, list) and current_step in quest_steps:
                    current_step_index = quest_steps.index(current_step)
                    completed_step_ids = quest_steps[:current_step_index]
                    
                    # Get step data for completed steps
                    if completed_step_ids:
                        step_manager = self.airtable_multi_manager.get_manager("craffft_steps")
                        if step_manager:
                            for step_id in completed_step_ids:
                                step_info = step_manager.get_row("record_id", step_id)
                                if step_info:
                                    current_quest_completed_steps_info.append(step_info)
                
                student['current_quest_completed_steps'] = current_quest_completed_steps_info
            else:
                student['current_quest_name'] = ''
                student['current_quest_description'] = ''
                student['current_quest_completed_steps'] = []
                student['current_step_data'] = None

        return_data = {
            'quests': quest_data,
            'students': students
        }
        return return_data

    def get_teacher_data(self, classroom_id):
        """
        Retrieve the teacher for the classroom using a direct SQL query.
        Returns the first teacher found, or None if not found.
        """
        sql = f"SELECT * FROM craffft_teachers WHERE website_user_id = '{classroom_id}'"
        teachers = self.airtable_multi_manager.execute_sql_query('craffft_teachers', sql)
        if not teachers:
            return None
        return teachers[0]

    def get_student_info(self, student_id):
        """
        Retrieve a student's data by their ID.
        Returns the student data dict or None if not found.
        """
        sql = f"SELECT * FROM craffft_students WHERE website_id = '{student_id}'"
        students = self.airtable_multi_manager.execute_sql_query('craffft_students', sql)
        if not students:
            return None
        return students[0]

    def get_student_by_class(self, classroom_id):
        """
        Retrieve all students in a specific classroom.
        Returns a list of student data dicts or an empty list if none found.
        """
        sql = f"SELECT * FROM craffft_students WHERE current_class = '{classroom_id}'"
        return self.airtable_multi_manager.execute_sql_query('craffft_students', sql    )

    def update_step_and_check_quest(self, website_id, new_current_step, allow_quest_update=True):
        """
        Update student's current step and check if quest changed
        
        Args:
            website_id: Student's website ID
            new_current_step: New current step to set
            allow_quest_update: Whether to allow quest updates (default True)
        
        Returns:
            dict with keys:
                - current_step: Current step after update
                - current_quest: Current quest ID  
                - quest_changed: Boolean if quest was changed
                - success: Boolean if operation succeeded
                - error: Error message if operation failed
        """
        try:
            # Get managers
            student_manager = self.airtable_multi_manager.get_manager("craffft_students")
            step_manager = self.airtable_multi_manager.get_manager("craffft_steps")

            # Get current student data
            student_row = student_manager.get_row("website_id", website_id)
            if not student_row:
                return {
                    "success": False,
                    "error": f"No student found with website_id: {website_id}"
                }

            # Get current quest and step from craffft_students 
            parsed_student = parse_database_row(student_row)
            old_current_step = parsed_student.get("current_step", "")
            old_current_quest = parsed_student.get("current_quest", "")
            current_quest = old_current_quest if old_current_quest else ""
            
            # Use get_value_by_row_and_column to look up the quest for this step
            step_quest_id = step_manager.get_value_by_row_and_column("name", new_current_step, "craffft_quest_id")
            if not step_quest_id:
                return {
                    "success": False,
                    "error": f"No quest found for step {new_current_step} in craffft_steps table"
                }

            quest_changed = False
            if allow_quest_update:
                # Update current_step and allow quest changes
                success = student_manager.modify_field("website_id", website_id, "current_step", new_current_step)
                current_step = new_current_step

                # Check if quest needs to be updated
                if step_quest_id != old_current_quest:
                    # Quest has changed, update the current_quest
                    new_current_quest = step_quest_id  # Replace with new quest (string)
                    success = student_manager.modify_field("website_id", website_id, "current_quest", new_current_quest)
                    if success:
                        current_quest = new_current_quest
                        quest_changed = True
            else:
                # Quest update not allowed - validate that step belongs to current quest
                if step_quest_id != old_current_quest:
                    return {
                        "success": False,
                        "error": f"Step {new_current_step} belongs to quest {step_quest_id} which is not the student's current quest {old_current_quest}. Quest updates are disabled."
                    }

                # Step is valid for current quest, update current_step only
                success = student_manager.modify_field("website_id", website_id, "current_step", new_current_step)
                if not success:
                    return {
                        "success": False,
                        "error": f"Failed to update current_step for student with website_id: {website_id}"
                    }
                current_step = new_current_step

            # Update quest progress percentage and check for quest completion after step/quest changes
            quest_completed = False
            try:
                quest_manager = self.airtable_multi_manager.get_manager("craffft_quests")
                if quest_manager and current_quest:
                    # Get the current quest object
                    current_quest_obj = quest_manager.get_row("short_code", current_quest)
                    if current_quest_obj:
                        # Get updated student data for progress calculation
                        updated_student = student_manager.get_row("website_id", website_id)
                        # Calculate new progress
                        new_progress = StudentDataManager.get_progress(updated_student, current_quest_obj)
                        # Update progress in database
                        student_manager.modify_field("website_id", website_id, "quest_progress_percentage", new_progress)
                        
                        # Check if quest is completed (progress is 100%)
                        if float(new_progress) >= 100.0:
                            # Quest is completed - check if the student is on the last step
                            quest_completed = True
                            print(f"Quest {current_quest} completed for student {website_id}")
                            
                            # Get the student's completed quests array
                            parsed_updated_student = parse_database_row(updated_student)
                            completed_quests = parsed_updated_student.get("completed_quests", [])
                            
                            # Ensure completed_quests is a list
                            if not isinstance(completed_quests, list):
                                completed_quests = []
                            
                            # Add the current quest to completed quests if not already there
                            if current_quest not in completed_quests:
                                completed_quests.append(current_quest)
                                # Update completed_quests in the database
                                student_manager.modify_field("website_id", website_id, "completed_quests", completed_quests)
                            
                            # Set current_quest to null (empty string)
                            student_manager.modify_field("website_id", website_id, "current_quest", "")
                            current_quest = ""  # Update local variable for return value
                            
                            print(f"Quest {current_quest} moved to completed quests for student {website_id}")
                            
            except Exception as e:
                print(f"Warning: Failed to update quest progress: {e}")
                # Don't fail the whole operation if progress update fails

            return {
                "success": True,
                "current_step": current_step,
                "current_quest": current_quest,
                "quest_changed": quest_changed,
                "quest_completed": quest_completed
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }

    def add_classes_to_teacher_by_website_id(self, teacher_website_id: str, new_classes: set) -> dict:
        """
        Add classes to a teacher's classroom_ids field using their website_user_id.
        
        Args:
            teacher_website_id: The teacher's website_user_id to search for
            new_classes: Set of class IDs to add to the teacher's classroom_ids
            
        Returns:
            Dictionary with success status and details
        """
        try:
            # Get the teachers table manager
            teachers_manager = self.airtable_multi_manager.get_manager("craffft_teachers")
            if not teachers_manager:
                return {
                    "success": False,
                    "error": "craffft_teachers table not found"
                }
            
            # Find the teacher by website_user_id
            teacher_row = teachers_manager.get_row("website_user_id", teacher_website_id)
            if not teacher_row:
                return {
                    "success": False,
                    "error": f"Teacher with website_user_id '{teacher_website_id}' not found"
                }
            
            # Parse the teacher row to handle stringified data
            parsed_teacher = parse_database_row(teacher_row)
            current_classroom_ids = parsed_teacher.get('classroom_ids', [])
            
            # Ensure current_classroom_ids is a list
            if not isinstance(current_classroom_ids, list):
                current_classroom_ids = []
            
            # Convert current_classroom_ids to a set for efficient operations
            current_classes_set = set(current_classroom_ids)
            
            # Convert new_classes to strings (in case they're integers) and create set
            new_classes_str_set = {str(cls) for cls in new_classes}
            
            # Find classes that need to be added (set difference)
            classes_to_add = new_classes_str_set - current_classes_set
            
            if not classes_to_add:
                return {
                    "success": True,
                    "message": "No new classes to add - all classes already exist",
                    "teacher_name": f"{teacher_row.get('first_name', '')} {teacher_row.get('last_name', '')}".strip(),
                    "teacher_website_id": teacher_website_id,
                    "current_classes": current_classroom_ids,
                    "classes_added": []
                }
            
            # Add new classes to the existing list
            updated_classroom_ids = current_classroom_ids + list(classes_to_add)
            
            # Update the teacher's classroom_ids field in the database
            success = teachers_manager.modify_field(
                column_containing_reference="website_user_id",
                reference_value=teacher_website_id,
                target_column="classroom_ids",
                new_value=updated_classroom_ids
            )
            
            if success:
                # Mark table as modified for Airtable sync
                self.airtable_multi_manager.mark_table_as_modified("craffft_teachers")
                
                return {
                    "success": True,
                    "message": f"Successfully added {len(classes_to_add)} classes to teacher",
                    "teacher_name": f"{teacher_row.get('first_name', '')} {teacher_row.get('last_name', '')}".strip(),
                    "teacher_website_id": teacher_website_id,
                    "classes_added": list(classes_to_add),
                    "updated_classes": updated_classroom_ids,
                    "previous_classes": current_classroom_ids
                }
            else:
                return {
                    "success": False,
                    "error": "Failed to update classroom_ids in database"
                }
                
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }