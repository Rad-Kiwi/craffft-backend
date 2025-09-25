import os
import json
import datetime
import decimal
import ast
from dotenv import load_dotenv, find_dotenv

critical_tables = ['craffft_students', 'craffft_teachers', 'craffft_quests']


def is_ci_testing_mode():
    """
    Check if we're running in CI testing mode with mock credentials.
    
    Returns:
        bool: True if in CI testing mode, False otherwise
    """
    is_ci = os.getenv('CI_TESTING', '').lower() == 'true'
    base_id = os.getenv('AIRTABLE_BASE_ID', '')
    api_key = os.getenv('AIRTABLE_API_KEY', '')
    
    # Check if using mock values
    is_mock = (base_id.startswith('mock_') or 
               api_key.startswith('mock_') or
               base_id == 'your_base_id' or
               api_key == 'your_airtable_api_key')
    
    return is_ci or is_mock


def skip_if_no_real_credentials(test_name="test"):
    """
    Skip a test if we don't have real Airtable credentials.
    
    Args:
        test_name: Name of the test being skipped
        
    Returns:
        bool: True if test should be skipped, False if it should run
    """
    if is_ci_testing_mode():
        print(f"SKIP: {test_name} - Running in CI testing mode without real Airtable credentials")
        return True
    return False


# Load environment variables once at module import time
# Load .env first (defaults), then .env.local (overrides)
# Use find_dotenv to gracefully handle missing files
env_file = find_dotenv('.env')
env_local_file = find_dotenv('.env.local')

if env_file:
    load_dotenv(env_file)
if env_local_file:
    load_dotenv(env_local_file, override=True)

def load_env(KEY_NAME, fallback=None, check_system=True):
    """
    Load a value from environment variables with flexible source checking.
    
    Args:
        KEY_NAME (str): The environment variable name to load
        fallback (str, optional): Default value to return if variable is not found
        check_system (bool): Whether to check system environment variables (always True with os.getenv)
    
    Priority order (os.getenv automatically checks all sources):
    1. System environment variables (set by CI/CD, shell, etc.)
    2. Variables loaded from .env.local file (overrides)
    3. Variables loaded from .env file (defaults)
    
    Returns:
        str: The environment variable value or fallback
        
    Raises:
        ValueError: If the environment variable is not found and no fallback provided
    """
    value = os.getenv(KEY_NAME)
    
    if value:
        return value
    
    if fallback is not None:
        return fallback
    
    # Check if we're in CI testing mode
    is_ci_testing = os.getenv('CI_TESTING', '').lower() == 'true'
    
    # Build a helpful error message showing where we looked
    env_file_status = "✓ loaded" if find_dotenv('.env') else "✗ not found"
    env_local_status = "✓ loaded" if find_dotenv('.env.local') else "✗ not found" 
    
    if is_ci_testing:
        error_msg = (
            f"Environment variable '{KEY_NAME}' not found (CI Testing Mode).\n"
            f"Sources checked:\n"
            f"  - System environment variables\n"
            f"  - .env.local file ({env_local_status})\n"
            f"  - .env file ({env_file_status})\n"
            f"\nRunning in CI testing mode - some tests may be skipped."
        )
    else:
        error_msg = (
            f"Environment variable '{KEY_NAME}' not found.\n"
            f"Sources checked:\n"
            f"  - System environment variables\n"
            f"  - .env.local file ({env_local_status})\n"
            f"  - .env file ({env_file_status})\n"
            f"\nFor CI/CD: Ensure secrets are configured in GitHub Actions.\n"
            f"For local development: Add '{KEY_NAME}=your_value' to .env.local file."
        )
    
    raise ValueError(error_msg)


def deep_jsonify(obj, max_depth=10, current_depth=0, parse_stringified_lists=True):
    """
    Convert a complex object with nested structures to a JSON-serializable format.
    Handles multiple levels of nesting including dicts, lists, tuples, sets, and custom objects.
    
    Args:
        obj: The object to serialize
        max_depth: Maximum recursion depth to prevent infinite loops
        current_depth: Current recursion depth (internal use)
        parse_stringified_lists: Whether to attempt parsing string representations of lists
    
    Returns:
        JSON-serializable version of the object
    """
    # Prevent infinite recursion
    if current_depth >= max_depth:
        return f"<max_depth_reached: {type(obj).__name__}>"
    
    # Handle None
    if obj is None:
        return None
    
    # Handle basic JSON-serializable types (but check strings for stringified lists)
    if isinstance(obj, str):
        # Try to parse stringified lists if enabled
        if parse_stringified_lists and obj.strip().startswith('[') and obj.strip().endswith(']'):
            try:
                import ast
                parsed = ast.literal_eval(obj)
                if isinstance(parsed, (list, tuple)):
                    return deep_jsonify(parsed, max_depth, current_depth + 1, parse_stringified_lists)
            except (ValueError, SyntaxError):
                # If parsing fails, return as string
                pass
        return obj
    
    if isinstance(obj, (int, float, bool)):
        return obj
    
    # Handle datetime objects
    if isinstance(obj, (datetime.datetime, datetime.date, datetime.time)):
        return obj.isoformat()
    
    # Handle decimal objects
    if isinstance(obj, decimal.Decimal):
        return float(obj)
    
    # Handle dictionaries
    if isinstance(obj, dict):
        return {
            str(key): deep_jsonify(value, max_depth, current_depth + 1, parse_stringified_lists)
            for key, value in obj.items()
        }
    
    # Handle lists and tuples
    if isinstance(obj, (list, tuple)):
        return [
            deep_jsonify(item, max_depth, current_depth + 1, parse_stringified_lists)
            for item in obj
        ]
    
    # Handle sets
    if isinstance(obj, set):
        return [
            deep_jsonify(item, max_depth, current_depth + 1, parse_stringified_lists)
            for item in obj
        ]
    
    # Handle custom objects by converting to dict
    if hasattr(obj, '__dict__'):
        return {
            key: deep_jsonify(value, max_depth, current_depth + 1, parse_stringified_lists)
            for key, value in obj.__dict__.items()
            if not key.startswith('_')  # Skip private attributes
        }
    
    # Fallback for any other type
    try:
        return str(obj)
    except Exception:
        return f"<non_serializable: {type(obj).__name__}>"


def safe_jsonify(obj, **kwargs):
    """
    Safely convert an object to JSON string with deep serialization.
    
    Args:
        obj: Object to serialize
        **kwargs: Additional arguments passed to json.dumps()
    
    Returns:
        JSON string representation of the object
    """
    try:
        serializable_obj = deep_jsonify(obj)
        return json.dumps(serializable_obj, indent=2, **kwargs)
    except Exception as e:
        return json.dumps({
            "error": f"Serialization failed: {str(e)}",
            "type": type(obj).__name__
        }, indent=2)


def convert_value_for_airtable(value):
    """
    Convert a database value to the appropriate format for Airtable.
    Detects stringified lists, numbers, and converts them appropriately.
    
    Args:
        value: The value to convert
    
    Returns:
        Converted value - lists as arrays, numbers as numbers, everything else as strings
    """
    if value is None:
        return None
    
    # Handle empty strings
    if isinstance(value, str) and not value.strip():
        return None  # Return None for empty strings instead of empty string
    
    if isinstance(value, str):
        stripped = value.strip()
        
        # Check if it looks like a stringified list
        if stripped.startswith('[') and stripped.endswith(']'):
            try:
                parsed_value = ast.literal_eval(stripped)
                if isinstance(parsed_value, (list, tuple)):
                    return str(parsed_value)  # Convert tuples to str
            except (ValueError, SyntaxError):
                pass  # If parsing fails, fall through to check for numbers
        
        # Check if it's a number string
        if stripped:
            # Try integer first
            try:
                return int(stripped)
            except ValueError:
                # Try float
                try:
                    return float(stripped)
                except ValueError:
                    pass  # Not a number, fall through to return as string
        
        # Return as string if not a list or number
        return value
    
    # If it's already a number, keep it as is
    if isinstance(value, (int, float)):
        return value
    
    # For other types, convert to string
    return str(value)


def parse_database_row(row):
    """
    Specialized function to parse database rows that may contain stringified lists.
    This is optimized for your specific use case with Airtable data.
    
    Args:
        row: Dictionary representing a database row
    
    Returns:
        Parsed row with stringified lists converted to actual lists
    """
    if not isinstance(row, dict):
        return deep_jsonify(row, parse_stringified_lists=True)
    
    parsed_row = {}
    for key, value in row.items():
        if isinstance(value, str):
            # Check if it looks like a stringified list
            stripped = value.strip()
            if stripped.startswith('[') and stripped.endswith(']'):
                try:
                    import ast
                    parsed_value = ast.literal_eval(stripped)
                    if isinstance(parsed_value, (list, tuple)):
                        parsed_row[key] = list(parsed_value)  # Convert tuples to lists
                    else:
                        parsed_row[key] = value  # Keep as string if not a list/tuple
                except (ValueError, SyntaxError):
                    parsed_row[key] = value  # Keep as string if parsing fails
            else:
                parsed_row[key] = value
        else:
            parsed_row[key] = deep_jsonify(value, parse_stringified_lists=True)
    
    return parsed_row


def process_quest_data_for_frontend(quest_data):
    """
    Process quest data to make it ready for frontend consumption.
    Ensures all required fields are present and properly formatted.
    
    Args:
        quest_data: List of quest objects from database
        
    Returns:
        List of processed quest objects with frontend-ready structure
    """
    processed_quests = []
    
    if not quest_data or not isinstance(quest_data, list):
        return processed_quests
        
    for quest in quest_data:
        try:
            # Parse the quest data to handle stringified fields
            parsed_quest = parse_database_row(quest)
            
            # Create frontend-ready quest object with all required fields
            processed_quest = {
                'record_id': parsed_quest.get('record_id', ''),
                'quest_name': parsed_quest.get('quest_name', 'Unnamed Quest'),
                'quest_description': parsed_quest.get('quest_description', 'No description available'),
                'quest_image': parsed_quest.get('quest_image', '/default-quest-image.png'),  # Fallback image
                'teacher_resource_url': parsed_quest.get('teacher_resource_url', '#'),  # Fallback URL
                'steps': parsed_quest.get('steps', []),
                'num_steps': len(parsed_quest.get('steps', [])),  # Calculate from steps array
                # Add any other fields that might be useful for frontend
                'difficulty': parsed_quest.get('difficulty', 'Medium'),
                'estimated_time': parsed_quest.get('estimated_time', 'Unknown'),
            }
            
            processed_quests.append(processed_quest)
            
        except Exception as e:
            print(f"Error processing quest data: {e}")
            # Add a minimal quest object to prevent frontend crashes
            processed_quests.append({
                'record_id': quest.get('record_id', ''),
                'quest_name': 'Error Loading Quest',
                'quest_description': 'There was an error loading this quest.',
                'quest_image': '/error-image.png',
                'teacher_resource_url': '#',
                'steps': [],
                'num_steps': 0,
                'difficulty': 'Unknown',
                'estimated_time': 'Unknown',
            })
    
    return processed_quests
