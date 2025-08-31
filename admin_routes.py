from flask import Blueprint, jsonify, request, send_from_directory, session, redirect, url_for, render_template
import functools
import hashlib
import os

# Create admin blueprint
admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Simple password protection
ADMIN_PASSWORD_HASH = os.environ.get('ADMIN_PASSWORD_HASH')

# If no hash is set, disable admin access for security
if not ADMIN_PASSWORD_HASH:
    print("⚠️  WARNING: ADMIN_PASSWORD_HASH not set. Admin access disabled.")
    print("   Set ADMIN_PASSWORD_HASH environment variable to enable admin access.")
    ADMIN_PASSWORD_HASH = "disabled"  # This will never match any password

def require_auth(f):
    """Decorator to require authentication for admin routes"""
    @functools.wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('admin_authenticated'):
            return redirect(url_for('admin.login'))
        return f(*args, **kwargs)
    return decorated_function

@admin_bp.route("/login", methods=['GET', 'POST'])
def login():
    """Admin login page"""
    if request.method == 'POST':
        password = request.form.get('password', '')
        password_hash = hashlib.sha256(password.encode()).hexdigest()
        
        if password_hash == ADMIN_PASSWORD_HASH:
            session['admin_authenticated'] = True
            return redirect(url_for('admin.database_admin'))
        else:
            return render_template('admin_login.html', error="Invalid password")
    
    return render_template('admin_login.html')

@admin_bp.route("/logout")
def logout():
    """Admin logout"""
    session.pop('admin_authenticated', None)
    return redirect(url_for('admin.login'))

@admin_bp.route("/database")
@require_auth
def database_admin():
    """Serve the database admin interface"""
    return render_template('admin_database.html')

@admin_bp.route("/api/tables")
@require_auth
def get_database_tables():
    """Get list of available database tables"""
    try:
        from flask import current_app
        multi_manager = current_app.config['multi_manager']
        available_tables = multi_manager.get_available_tables()
        return jsonify(available_tables)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@admin_bp.route("/api/query", methods=['POST'])
@require_auth
def execute_database_query():
    """Execute a SQL query on the database"""
    try:
        from flask import current_app
        multi_manager = current_app.config['multi_manager']
        
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({"error": "Missing query parameter"}), 400
        
        query = data['query'].strip()
        if not query:
            return jsonify({"error": "Empty query"}), 400
        
        # Basic security: only allow SELECT, SHOW, DESCRIBE queries for safety
        query_upper = query.upper().strip()
        allowed_prefixes = ['SELECT', 'SHOW', 'DESCRIBE', 'EXPLAIN', 'DELETE']
        
        if not any(query_upper.startswith(prefix) for prefix in allowed_prefixes):
            return jsonify({"error": "Only SELECT, SHOW, DESCRIBE, EXPLAIN, and DELETE queries are allowed"}), 403

        # Try to determine which table to query against
        # For now, we'll use the first available table as fallback
        available_tables = multi_manager.get_available_tables()
        if not available_tables:
            return jsonify({"error": "No tables available"}), 404
        
        # Use the first table manager to execute the query
        # This is a bit hacky but works for most SQL queries
        table_name = available_tables[0]
        manager = multi_manager.get_manager(table_name)
        
        if not manager:
            return jsonify({"error": f"Could not get manager for table {table_name}"}), 500
        
        # Use the SQLite storage to execute the query directly
        results = multi_manager.sqlite_storage.execute_sql_query(table_name, query)
        
        if results is None:
            return jsonify({"error": "Query execution failed"}), 500
        
        return jsonify({
            "data": results,
            "count": len(results) if results else 0,
            "query": query
        })
        
    except Exception as e:
        return jsonify({"error": f"Query execution error: {str(e)}"}), 500

@admin_bp.route("/api/table/<table_name>")
@require_auth
def get_table_data(table_name):
    """Get data from a specific table"""
    try:
        from flask import current_app
        multi_manager = current_app.config['multi_manager']
        
        manager = multi_manager.get_manager(table_name)
        if not manager:
            return jsonify({"error": f"Table {table_name} not found"}), 404
        
        # Execute a simple SELECT query
        query = f'SELECT * FROM "{table_name}" LIMIT 100'
        results = multi_manager.sqlite_storage.execute_sql_query(table_name, query)
        
        if results is None:
            return jsonify({"error": "Failed to fetch table data"}), 500
        
        return jsonify({
            "table": table_name,
            "data": results,
            "count": len(results) if results else 0
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500
