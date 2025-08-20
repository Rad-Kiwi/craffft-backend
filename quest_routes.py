from flask import Blueprint, render_template, request, jsonify
import uuid

# Create a Blueprint for quest routes
quest_bp = Blueprint('quests', __name__)


@quest_bp.route("/quest-generator", methods=['GET'])
def quest_generator_form():
    """
    Serve the quest generation form UI
    """
    return render_template('quest_generator.html')


@quest_bp.route("/quest-browser", methods=['GET'])
def quest_browser():
    """
    Serve the quest browser UI
    """
    return render_template('quest_browser.html')


@quest_bp.route("/api/quests", methods=['GET'])
def get_all_quests():
    """
    Get all quests from the database
    """
    from flask import current_app
    
    try:
        multi_manager = current_app.config['multi_manager']
        quests_manager = multi_manager.get_manager("craffft_quests")
        if not quests_manager:
            return jsonify({"error": "craffft_quests table not found"}), 404
        
        quests = quests_manager.get_full_table()
        return jsonify(quests)
    
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve quests: {str(e)}"}), 500


@quest_bp.route("/api/quests/<record_id>", methods=['GET'])
def get_quest_by_id(record_id):
    """
    Get a specific quest by record_id
    """
    from flask import current_app
    
    try:
        multi_manager = current_app.config['multi_manager']
        quests_manager = multi_manager.get_manager("craffft_quests")
        if not quests_manager:
            return jsonify({"error": "craffft_quests table not found"}), 404
        
        # Use get_row to fetch specific quest
        quest = quests_manager.get_row(record_id)
        if quest:
            return jsonify(quest)
        else:
            return jsonify({"error": "Quest not found"}), 404
    
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve quest: {str(e)}"}), 500


@quest_bp.route("/api/steps", methods=['GET'])
def get_all_steps():
    """
    Get all steps from the database
    """
    from flask import current_app
    
    try:
        multi_manager = current_app.config['multi_manager']
        steps_manager = multi_manager.get_manager("craffft_steps")
        if not steps_manager:
            return jsonify({"error": "craffft_steps table not found"}), 404
        
        steps = steps_manager.get_full_table()
        return jsonify(steps)
    
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve steps: {str(e)}"}), 500


@quest_bp.route("/api/steps/<step_name>", methods=['GET'])
def get_step_by_name(step_name):
    """
    Get a specific step by name/short_code from craffft_steps table
    """
    from flask import current_app
    
    try:
        multi_manager = current_app.config['multi_manager']
        steps_manager = multi_manager.get_manager("craffft_steps")
        if not steps_manager:
            return jsonify({"error": "craffft_steps table not found"}), 404
        
        # Get all steps and find the one matching the name
        all_steps = steps_manager.get_full_table()
        step = None
        for s in all_steps:
            if s.get('name') == step_name or s.get('short_code') == step_name:
                step = s
                break
        
        if step:
            return jsonify(step)
        else:
            return jsonify({"error": "Step not found"}), 404
    
    except Exception as e:
        return jsonify({"error": f"Failed to retrieve step: {str(e)}"}), 500


@quest_bp.route("/generate-quest", methods=['POST'])
def generate_quest():
    """
    Generate a new quest and create associated steps with individual descriptions
    """
    from flask import current_app
    
    try:
        multi_manager = current_app.config['multi_manager']
        
        data = request.get_json()
        if not data:
            return jsonify({"error": "Missing JSON body"}), 400

        # Validate required fields for quest
        required_quest_fields = [
            'quest_name', 'quest_prefix', 'quest_description'
        ]
        
        for field in required_quest_fields:
            if not data.get(field):
                return jsonify({"error": f"Missing required field: {field}"}), 400

        # Validate step data
        step_codes = data.get('step_codes', [])
        step_descriptions = data.get('step_descriptions', [])
        step_locations = data.get('step_locations', [])
        step_curriculum_alignments = data.get('step_curriculum_alignments', [])
        step_description_curriculum_alignments = data.get('step_description_curriculum_alignments', [])
        
        if not step_codes or not step_descriptions or not step_locations or not step_curriculum_alignments:
            return jsonify({"error": "At least one step with description, location, and curriculum alignment is required"}), 400
            
        if (len(step_codes) != len(step_descriptions) or 
            len(step_codes) != len(step_locations) or 
            len(step_codes) != len(step_curriculum_alignments)):
            return jsonify({"error": "Number of step codes must match number of step descriptions, locations, and curriculum alignments"}), 400

        # Get the managers
        quests_manager = multi_manager.get_manager("craffft_quests")
        steps_manager = multi_manager.get_manager("craffft_steps")
        
        if not quests_manager:
            return jsonify({"error": "craffft_quests table not found"}), 404
        if not steps_manager:
            return jsonify({"error": "craffft_steps table not found"}), 404

        # Generate quest record ID if not provided
        quest_record_id = data.get('record_id')
        if not quest_record_id:
            quest_record_id = f"rec{str(uuid.uuid4()).replace('-', '')[:10]}"

        # Create step records with individual descriptions and locations
        created_steps = []
        step_record_ids = []
        
        for i, (step_code, step_description, step_location, step_curriculum_alignment) in enumerate(zip(step_codes, step_descriptions, step_locations, step_curriculum_alignments)):
            if not step_code.strip() or not step_description.strip() or not step_location.strip() or not step_curriculum_alignment.strip():
                continue
                
            # Generate step record ID
            step_record_id = f"rec{str(uuid.uuid4()).replace('-', '')[:10]}"
            
            # Create step record
            step_record = {
                'record_id': step_record_id,
                'name': step_code.strip(),  # Use step code as name
                'craffft_curriculum_alignment': step_curriculum_alignment.strip(),
                'location': step_location.strip(),  # Individual location for each step
                'description': step_description.strip(),
                'craffft_quests': quest_record_id,  # Link to the quest
            }
            
            # Add description curriculum alignment if provided
            if (i < len(step_description_curriculum_alignments) and 
                step_description_curriculum_alignments[i] and 
                step_description_curriculum_alignments[i].strip()):
                step_record['description_curriculum_alignment'] = step_description_curriculum_alignments[i].strip()
            
            # Add the step to the database
            success = steps_manager.add_record(step_record)
            if success:
                created_steps.append(step_code.strip())
                step_record_ids.append(step_record_id)
            else:
                print(f"Warning: Failed to create step {step_code}")

        # Create the quest record
        quest_record = {
            'record_id': quest_record_id,
            'quest_name': data['quest_name'],
            'step_short_code': data['quest_prefix'],  # Use quest prefix as step_short_code
            'steps': str(step_codes) if step_codes else "[]",  # Store step codes as list string
            'quest_description': data['quest_description'],
            'num_steps': len(created_steps)
        }
        
        # Add quest image if provided
        if data.get('quest_image') and data['quest_image'].strip():
            quest_record['quest_image'] = data['quest_image'].strip()

        # Add the quest to the database
        success = quests_manager.add_record(quest_record)
        
        if success:
            # Mark tables as modified so they can be uploaded to Airtable later
            multi_manager.mark_table_as_modified("craffft_quests")
            multi_manager.mark_table_as_modified("craffft_steps")
            
            response_data = {
                "message": "Quest and steps generated successfully",
                "record_id": quest_record_id,
                "quest_name": data['quest_name'],
                "quest_prefix": data['quest_prefix'],
                "num_steps": len(created_steps),
                "steps_created": created_steps,
                "step_records_created": len(created_steps),
                "quest_record": quest_record
            }
            
            return jsonify(response_data), 201
        else:
            return jsonify({"error": "Failed to add quest to database"}), 500

    except Exception as e:
        return jsonify({"error": f"Unexpected error: {str(e)}"}), 500
