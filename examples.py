# Example usage of AirtableMultiManager
from airtable_multi_manager import AirtableMultiManager
from sqlite_storage import SQLiteStorage
from airtable_csv import AirtableCSVManager

import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv('.env.local')
load_dotenv('.env')

def example_basic_usage():
    """Basic usage example using environment variables."""
    
    # Create manager using environment variables
    multi_manager = AirtableMultiManager.from_environment()
    
    # Get available tables
    print("Available tables:", multi_manager.get_available_tables())
    
    # Access a specific table
    table_name = "DataHub_Craffft"
    
    # Get CSV data
    csv_data = multi_manager.get_csv_data(table_name)
    if csv_data:
        print(f"CSV data length for {table_name}: {len(csv_data)} characters")
    
    # Update from Airtable
    result = multi_manager.update_csv_from_airtable(table_name)
    print(f"Update result for {table_name}: {result}")
    
    # Convert to JSON
    json_data = multi_manager.convert_csv_to_json(table_name)
    if json_data:
        print(f"JSON data for {table_name}: {len(json_data)} records")


def example_custom_configuration():
    """Example with custom table configuration."""
    
    # Create manager with custom table names
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    
    # Specify which tables you want to manage
    table_names = ["DataHub_Craffft", "AnotherTable", "ThirdTable"]
    
    multi_manager = AirtableMultiManager(
        api_key=api_key, 
        base_id=base_id, 
        table_names=table_names
    )
    
    # Add a new table dynamically
    multi_manager.add_table("NewTable")
    
    print("All available tables:", multi_manager.get_available_tables())
    
    # Update all tables at once
    results = multi_manager.update_all_tables()
    for table, result in results.items():
        print(f"{table}: {result}")


def example_config_dict():
    """Example using configuration dictionary."""
    
    config = {
        'api_key': os.getenv('AIRTABLE_API_KEY'),
        'base_id': os.getenv('AIRTABLE_BASE_ID'),
        'table_names': ['DataHub_Craffft', 'Products', 'Customers']
    }
    
    multi_manager = AirtableMultiManager.from_config_dict(config)
    
    # Work with specific tables
    for table_name in multi_manager.get_available_tables():
        manager = multi_manager.get_manager(table_name)
        if manager:
            print(f"Manager for {table_name} is ready")


def example_error_handling():
    """Example with error handling."""
    
    try:
        multi_manager = AirtableMultiManager.from_environment()
        
        # Try to access a non-existent table
        result = multi_manager.get_csv_data("non-existent-table")
        if result is None:
            print("Table not found - this is expected")
        
        # Remove a table
        removed = multi_manager.remove_table("DataHub_Craffft")
        print(f"Table removed: {removed}")
        
        # Try to access removed table
        result = multi_manager.get_csv_data("DataHub_Craffft")
        if result is None:
            print("Table no longer available after removal")
            
    except ValueError as e:
        print(f"Configuration error: {e}")
    except Exception as e:
        print(f"Unexpected error: {e}")


def example_discover_tables():
    """Example of discovering tables from a base."""
    
    multi_manager = AirtableMultiManager.from_environment()
    
    # Get all table names from the configured base
    table_names = multi_manager.get_tables_from_base()
    print(f"Tables in base {multi_manager.base_id}: {table_names}")
    
    # Discover and add all tables from the base
    results = multi_manager.discover_and_add_tables_from_base()
    print(f"Added tables: {results}")
    
    # Now you can work with any discovered table
    for table_name in table_names or []:
        csv_data = multi_manager.get_csv_data(table_name)
        if csv_data:
            print(f"Table {table_name} has {len(csv_data)} characters of CSV data")




def example_update_all_tables():
    """Example of updating all tables in the configured base."""

    # Create manager using environment variables 
    multi_manager = AirtableMultiManager.from_environment()

    # Get all table names from the base
    table_names = multi_manager.get_tables_from_base()
    print(f"Tables in base {multi_manager.base_id}: {table_names}")
    
    # Discover anresults = multi_manager.discover_and_add_tables_from_base()d add all tables from the base
    results = multi_manager.discover_and_add_tables_from_base()
    print(f"Added tables: {results}")
    
    # Now you can work with any discovered table
    for table_name in table_names or []:
        csv_data = multi_manager.get_csv_data(table_name)
        if csv_data:
            print(f"Table {table_name} has {len(csv_data)} characters of CSV data")
    
    # Update all tables
    results = multi_manager.update_all_tables()
    
    for table, result in results.items():
        print(f"Update result for {table}: {result}")

def database_example():
    # Load environment variables
    load_dotenv('.env.local')

    # Initialize AirtableCSVManager with SQLiteStorage
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    table_name = "craffft_steps"  # Example table name

    sqlite_store = SQLiteStorage()
    manager = AirtableCSVManager(base_id, table_name, api_key, sqlite_storage=sqlite_store)

    # Update from Airtable and store in both file and DB
    manager.update_csv_from_airtable()

    # Read CSV from DB
    csv_data = manager.read_csv(from_db=True)


    print(f"CSV data length: {len(csv_data)} characters")


def database_columns_example():
    # Load environment variables
    load_dotenv('.env.local')

    # Initialize AirtableCSVManager with SQLiteStorage
    api_key = os.getenv('AIRTABLE_API_KEY')
    base_id = os.getenv('AIRTABLE_BASE_ID')
    table_name = "craffft_steps"  # Example table name

    sqlite_store = SQLiteStorage()
    manager = AirtableCSVManager(base_id, table_name, api_key, sqlite_storage=sqlite_store)

    # Update from Airtable and store in both file and DB
    manager.update_csv_from_airtable()

    # Use the same variable names as in app.py get-value-from-db
    column_containing_reference = "name"
    reference_value = "Garlic Hunt"
    target_column = "description"

    # Read Row from DB
    row = manager.get_row(column_containing_reference, reference_value)

    if row:
        print(f"Found row: {row}")
    else:
        print("Row not found")

    # Read specific value from DB
    value = manager.get_value_by_row_and_column(column_containing_reference, reference_value, target_column)
    if value:
        print(f"Found value: {value}")
    else:
        print("Value not found")


def database_value_retrieval_multi_manager():
    # Load environment variables
    load_dotenv('.env.local')

    # Initialize AirtableMultiManager 
    multi_manager = AirtableMultiManager.from_environment()
    
    multi_manager.discover_and_add_tables_from_base()

    # Use the same variable names as in app.py get-value-from-db
    column_containing_reference = "name"
    reference_value = "Garlic Hunt"
    target_column = "description"

    # Read specific value from DB
    value = multi_manager.get_value("craffft_steps", column_containing_reference, reference_value, target_column)
    
    if value:
        print(f"Found value: {value}")
    else:
        print("Value not found")

if __name__ == "__main__":
    # print("=== Basic Usage ===")
    # example_basic_usage()
    
    # print("\n=== Custom Configuration ===")
    # example_custom_configuration()
    
    # print("\n=== Config Dictionary ===")
    # example_config_dict()
    
    # print("\n=== Discover Tables ===")
    # example_discover_tables()

    # print("\n=== Update All Tables ===")
    # example_update_all_tables()
    #
    # print("\n=== Error Handling ===")
    # example_error_handling()

    # print("\n=== Database Example ===")
    # database_example()

    print("\n=== Database Columns Example ===")
    database_columns_example()

    print("\n=== Database Value Retrieval Multi Manager ===")
    database_value_retrieval_multi_manager()