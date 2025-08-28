import os
from typing import Dict, Optional, List
from airtable import Airtable
from table_manager import TableManager
from sqlite_storage import SQLiteStorage
from utilities import load_env
import requests


class AirtableMultiManager:
    """
    Manages multiple TableManager instances for tables within a single Airtable base.
    Allows easy access to different tables by table name.
    """
    
    def __init__(self, api_key: str, base_id: str, table_names: Optional[List[str]] = None, sqlite_storage: Optional[SQLiteStorage] = None):
        """
        Initialize the multi-manager for a single base.
        
        Args:
            api_key: The Airtable API key
            base_id: The Airtable base ID
            table_names: List of table names to manage. If None, will use default tables.
            sqlite_storage: Optional SQLiteStorage instance to use for all tables.
        """
        self.api_key = api_key
        self.base_id = base_id
        self.managers: Dict[str, TableManager] = {}
        self.sqlite_storage = sqlite_storage or SQLiteStorage()  # Always use a shared storage

        # Default table names if none provided
        if table_names is None:
            self.table_names = ["DataHub_Craffft"]  # Default table
        else:
            self.table_names = table_names
        
        # Initialize managers for all configured tables
        self._initialize_managers()
    
    def _initialize_managers(self):
        """Initialize TableManager instances for all configured tables."""
        for table_name in self.table_names:
            self.managers[table_name] = TableManager(
                base_id=self.base_id,
                table_name=table_name,
                api_key=self.api_key,
                sqlite_storage=self.sqlite_storage  # Pass shared storage
            )
    
    def add_table(self, table_name: str):
        """
        Add a new table to the manager.
        
        Args:
            table_name: Name of the table
        """
        if table_name not in self.table_names:
            self.table_names.append(table_name)
        self.managers[table_name] = TableManager(
            base_id=self.base_id,
            table_name=table_name,
            api_key=self.api_key,
            sqlite_storage=self.sqlite_storage  # Pass shared storage
        )
    
    def get_manager(self, table_name: str) -> Optional[TableManager]:
        """
        Get the TableManager for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            TableManager instance or None if table not found
        """
        return self.managers.get(table_name)
    
    def get_csv_data(self, table_name: str) -> Optional[str]:
        """
        Get CSV data for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            CSV data as string or None if not found
        """
        manager = self.get_manager(table_name)
        if manager:
            return manager.read_csv()
        return None
    
    def update_database_from_airtable(self, table_name: str) -> Optional[str]:
        """
        Update CSV file from Airtable for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            Success message or None if failed
        """
        manager = self.get_manager(table_name)
        if manager:
            return manager.update_database_from_airtable()
        return None
    
    def get_table_as_json(self, table_name: str):
        """
        Convert table to JSON for a specific table.
        
        Args:
            table_name: Name of the table
            
        Returns:
            JSON data or None if not found
        """
        manager = self.get_manager(table_name)
        if manager:
            return manager.get_table_as_json()
        return None
    
    def update_all_tables(self) -> Dict[str, str]:
        """
        Update CSV files from Airtable for all configured tables.
        
        Returns:
            Dictionary with table names as keys and status messages as values
        """
        results = {}
        for table_name in self.managers.keys():
            try:
                result = self.update_database_from_airtable(table_name)
                results[table_name] = result if result else "Failed to update"
            except Exception as e:
                results[table_name] = f"Error: {str(e)}"
        return results
    
    def get_available_tables(self) -> list:
        """
        Get list of all available table names.
        
        Returns:
            List of table names
        """
        return list(self.managers.keys())
    
    def remove_table(self, table_name: str) -> bool:
        """
        Remove a table from the manager.
        
        Args:
            table_name: Name of the table to remove
            
        Returns:
            True if removed successfully, False if table not found
        """
        if table_name in self.managers:
            del self.managers[table_name]
            if table_name in self.table_names:
                self.table_names.remove(table_name)
            return True
        return False
    
    @classmethod
    def from_environment(cls) -> 'AirtableMultiManager':
        """
        Create an instance using environment variables.
        Expects AIRTABLE_API_KEY and AIRTABLE_BASE_ID to be set.
        
        Returns:
            AirtableMultiManager instance
        """
        api_key = load_env('AIRTABLE_API_KEY')
        base_id = load_env('AIRTABLE_BASE_ID')
        
        # Use a shared SQLiteStorage instance
        sqlite_storage = SQLiteStorage()
        return cls(api_key=api_key, base_id=base_id, sqlite_storage=sqlite_storage)

    @classmethod
    def from_config_dict(cls, config: Dict[str, str]) -> 'AirtableMultiManager':
        """
        Create an instance from a configuration dictionary.
        
        Args:
            config: Dictionary with 'api_key', 'base_id', and optionally 'table_names' keys.
        
        Returns:
            AirtableMultiManager instance
        """
        api_key = config.get('api_key')
        base_id = config.get('base_id')
        table_names = config.get('table_names')
        
        if not api_key:
            raise ValueError("api_key is required in config")
        if not base_id:
            raise ValueError("base_id is required in config")
        
        sqlite_storage = SQLiteStorage()
        return cls(api_key=api_key, base_id=base_id, table_names=table_names, sqlite_storage=sqlite_storage)
    

    def get_tables_from_base(self, base_id: str = None) -> Optional[List[str]]:
        """
        Get all table names from a specific Airtable base.
        
        Args:
            base_id: The Airtable base ID to query (uses instance base_id if None)
            
        Returns:
            List of table names or None if failed to retrieve
        """
        if base_id is None:
            base_id = self.base_id
            
        try:
            headers = {
                'Authorization': f'Bearer {self.api_key}',
                'Content-Type': 'application/json'
            }
            
            # Airtable Meta API endpoint for base schema
            url = f'https://api.airtable.com/v0/meta/bases/{base_id}/tables'
            
            response = requests.get(url, headers=headers)
            
            if response.status_code == 200:
                data = response.json()
                return [table['name'] for table in data.get('tables', [])]
            else:
                print(f"Failed to get tables from base {base_id}: {response.status_code}")
                print(f"Response: {response.text}")
                return None
                
        except Exception as e:
            print(f"Error getting tables from base {base_id}: {str(e)}")
            return None
    
    def discover_and_add_tables_from_base(self) -> Dict[str, bool]:
        """
        Discover all tables in the configured base and add them to the manager.
        
        Returns:
            Dictionary with table names as keys and success status as values
        """
        results = {}
        table_names = self.get_tables_from_base()
        
        if table_names:
            for table_name in table_names:
                try:
                    self.add_table(table_name)
                    results[table_name] = True
                except Exception as e:
                    print(f"Failed to add table {table_name}: {str(e)}")
                    results[table_name] = False
        else:
            print(f"No tables found or failed to retrieve tables from base {self.base_id}")
        
        return results

    def get_value(self, table_name: str, column_containing_reference: str, reference_value: str, target_column: str):
        """
        Retrieve a value from a specific column for the row where column_containing_reference == reference_value
        in the specified table using the relevant TableManager.

        Args:
            table_name: Name of the table
            column_containing_reference: Column to look up the row
            reference_value: Value to match in the lookup column
            target_column: Column from which to retrieve the value

        Returns:
            The value if found, otherwise None
        """
        manager = self.get_manager(table_name)
        if manager:
            return manager.get_value_by_row_and_column(column_containing_reference, reference_value, target_column)
        return None

    def execute_sql_query(self, table_name: str, sql_query: str):
        """
        Execute an arbitrary SQL query on the specified table using the SQLite backend.
        Returns a list of dicts (rows) or None if not available.
        """
        manager = self.get_manager(table_name)
        if manager:
            return manager.execute_sql_query(sql_query)
        return None

    def upload_modified_tables_to_airtable(self, force_upload: bool = False) -> Dict[str, str]:
        """
        Upload all modified tables back to Airtable.
        This will check which tables have been modified and upload their data back to Airtable.
        
        Args:
            force_upload: If True, upload all tables regardless of modification status
        
        Returns:
            Dictionary with table names as keys and status messages as values
        """
        results = {}
        for table_name in self.managers.keys():
            try:
                manager = self.get_manager(table_name)
                if manager and (force_upload or (hasattr(manager, 'has_updates') and manager.has_updates)):
                    result = manager.upload_to_airtable()
                    results[table_name] = result if result else "Failed to upload"
                    # Reset the update flag after successful upload
                    if result and not result.startswith("Error"):
                        manager.has_updates = False
                else:
                    results[table_name] = "No modifications to upload"
            except Exception as e:
                results[table_name] = f"Error: {str(e)}"
        return results

    def upload_table_to_airtable(self, table_name: str) -> Optional[str]:
        """
        Upload a specific table back to Airtable.
        
        Args:
            table_name: Name of the table to upload
            
        Returns:
            Success message or None if failed
        """
        manager = self.get_manager(table_name)
        if manager:
            return manager.upload_to_airtable()
        return None

    def mark_table_as_modified(self, table_name: str):
        """
        Mark a table as modified so it will be uploaded on the next sync.
        
        Args:
            table_name: Name of the table to mark as modified
        """
        manager = self.get_manager(table_name)
        if manager:
            manager.has_updates = True

    def get_modified_tables(self) -> List[str]:
        """
        Get a list of tables that have been modified and need to be uploaded.
        
        Returns:
            List of table names that have modifications
        """
        modified_tables = []
        for table_name in self.managers.keys():
            manager = self.get_manager(table_name)
            if manager and hasattr(manager, 'has_updates') and manager.has_updates:
                modified_tables.append(table_name)
        return modified_tables
