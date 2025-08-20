from utilities import parse_database_row
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
        Returns a string formatted to two decimal places.
        """
        if not current_quest_obj or 'steps' not in current_quest_obj or 'num_steps' not in current_quest_obj:
            print('Missing quest object')
            return "0.00"
        
        # Parse the student data to ensure completed_steps is a list
        parsed_student = parse_database_row(student)
        completed_steps = parsed_student.get('completed_steps', [])
        
        # Parse the quest object to ensure steps is a list
        parsed_quest = parse_database_row(current_quest_obj)
        quest_steps = parsed_quest.get('steps', [])
        
        # Ensure we have lists to work with
        if not isinstance(completed_steps, list):
            completed_steps = []
        if not isinstance(quest_steps, list):
            quest_steps = []

        # Check which completed steps can be found in the quest    
        intersection = [step for step in completed_steps if step in quest_steps]
        
        # Ensure num_steps is an integer
        num_steps_raw = parsed_quest.get('num_steps', 0)
        try:
            current_quest_step_total = int(num_steps_raw) if num_steps_raw else 0
        except (ValueError, TypeError):
            current_quest_step_total = 0
        
        if not current_quest_step_total:
            return "0.00"
        current_quest_progress = len(intersection) / current_quest_step_total if intersection else 0
        progress = "{:.2f}".format(current_quest_progress * 100)
        return progress

    def get_students_data_for_dashboard(self, classroom_id):
        # Retrieve the students for the classroom
        students = self.get_student_by_class(classroom_id)

        unique_quests = []
        for student in students:
            # current quest can be a list, so we need to ensure it's handled correctly
            current_quest = parse_database_row(student).get('current_quest')
            if not current_quest or not isinstance(current_quest, list) or not current_quest:
                continue
            quest_id = current_quest[0]
            # Check if any item in the unique_quests list matches the current_quest string exactly
            if quest_id not in unique_quests:
                print("adding " + quest_id)
                unique_quests.append(quest_id)

        # Create a SQL query to retrieve quests based on the unique quest IDs
        ids_str = "', '".join(unique_quests)
        sql = f"SELECT * FROM craffft_quests WHERE record_id IN ('{ids_str}')"

        # Retrieve the information about only those quests
        quest_data = self.airtable_multi_manager.execute_sql_query(
            'craffft_quests',
            sql
        )
        
        # Collect all step IDs from all quests
        steps_id_array = []
        for obj in quest_data:
            parsed_quest = parse_database_row(obj)
            steps = parsed_quest.get('steps', [])
            if isinstance(steps, list):
                steps_id_array.extend(steps)
        # Remove duplicates
        steps_id_array = list(dict.fromkeys(steps_id_array))
        student_data = []

        # Get the steps data for the quests
        sql = StudentDataManager.get_steps_sql('record_id', steps_id_array)
        step_data = self.airtable_multi_manager.execute_sql_query(
            'craffft_steps',
            sql
        )
        
        # If step_data failed (table doesn't exist), use empty list to prevent crashes
        if step_data is None:
            print("Warning: Failed to retrieve step data - table may not exist")
            step_data = []

        # Calculate progress for each student on current quest
        for student in students:
            # get the current quest ID
            current_quest = parse_database_row(student).get('current_quest')
            if not current_quest or not isinstance(current_quest, list) or not current_quest:
                continue
            current_quest_id = current_quest[0]  # they can only have 1 current quest
            # get total steps for that current quest
            current_quest_obj = next((obj for obj in quest_data if obj.get('record_id') == current_quest_id), None)
            # get progress
            student['progress'] = StudentDataManager.get_progress(student, current_quest_obj)
            # fill in current Quest details
            if current_quest_obj:
                student['current_quest_name'] = current_quest_obj.get('quest_name', '')
                student['current_quest_description'] = current_quest_obj.get('quest_description', '')
                # fill in current step details
                parsed_student = parse_database_row(student)
                parsed_quest = parse_database_row(current_quest_obj)
                completed_steps = parsed_student.get('completed_steps', [])
                quest_steps = parsed_quest.get('steps', [])
                
                # Ensure we have lists to work with
                if not isinstance(completed_steps, list):
                    completed_steps = []
                if not isinstance(quest_steps, list):
                    quest_steps = []

                # Find which steps match the quest    
                intersection = [value for value in completed_steps if value in quest_steps]
                index = len(intersection)
                # get the id of the next one. Safe lookup
                next_step_id = quest_steps[index] if index < len(quest_steps) else None
                current_quest_completed_steps_info = []
                for element in intersection:
                    print(element)
                    current_quest_completed_steps_info.append(StudentDataManager.get_step_data_by_key(element, step_data, 'record_id'))
                student['current_quest_completed_steps'] = current_quest_completed_steps_info
                student['current_step_data'] = StudentDataManager.get_step_data_by_key(next_step_id, step_data, 'record_id')
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
            step_quest_id = step_manager.get_value_by_row_and_column("name", new_current_step, "craffft_quests")
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

            return {
                "success": True,
                "current_step": current_step,
                "current_quest": current_quest,
                "quest_changed": quest_changed
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Unexpected error: {str(e)}"
            }