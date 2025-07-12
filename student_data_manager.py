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
            return "0.00"
        intersection = [value for value in student.get('completed_steps', []) if value in current_quest_obj['steps']]
        current_quest_step_total = current_quest_obj['num_steps']
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
            # Defensive: ensure current_quest is a list and not empty
            current_quest = student.get('current_quest')
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
            steps = obj.get('steps', [])
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

        # Calculate progress for each student on current quest
        for student in students:
            # get the current quest ID
            current_quest = student.get('current_quest')
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
                completed_steps = student.get('completed_steps', [])
                quest_steps = current_quest_obj.get('steps', [])
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