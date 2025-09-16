# craffft-backend

This is the backend API for the CRAFFFT educational platform, providing data management and student progress tracking functionality.

Currently deployed here:
https://craffft-api-e21e23f89690.herokuapp.com/

The backend manages multiple Airtable tables containing student data, teacher information, quests, steps, and curriculum data. It provides RESTful API endpoints for the frontend application and handles data synchronization between Airtable and a local/cloud database.

## Features

- **Multi-table Airtable Integration**: Automatically discovers and syncs multiple tables from Airtable
- **Student Progress Tracking**: Calculates student progress on educational quests and steps  
- **Teacher Dashboard Support**: Provides aggregated data for classroom management
- **Database Abstraction**: Supports both SQLite (development) and PostgreSQL (production)
- **Automatic Data Sync**: Daily scheduled updates from Airtable
- **Deep JSON Serialization**: Handles complex data structures including stringified lists
- **Interactive API Documentation**: Comprehensive Swagger/OpenAPI documentation with live testing

## API Documentation

The backend includes comprehensive interactive API documentation powered by Swagger/OpenAPI:

- **Local Development**: `http://localhost:5000/docs/`
- **Production**: `https://craffft-api-e21e23f89690.herokuapp.com/docs/`

Features:
- 📚 Interactive documentation for all endpoints
- 🧪 "Try it out" functionality for live API testing
- 📋 Complete request/response schemas with examples
- 🎯 Organized by functional areas (Students, Teachers, Quests, Database, Sync)
- 📖 Detailed descriptions and usage instructions

See the [`docs/`](./docs/) folder for documentation source files.


## Installation

1. Clone the repository.
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Environment Variables

Create a `.env.local` file in the project root with the following content:

```
AIRTABLE_BASE_ID=your_base_id
AIRTABLE_API_KEY=your_airtable_api_key
ENVIRONMENT_MODE=Development
```

**Required Variables:**
- `AIRTABLE_BASE_ID` — Your Airtable base ID
- `AIRTABLE_API_KEY` — Your Airtable API key with read/write permissions

**Optional Variables:**
- `ENVIRONMENT_MODE` — Set to `Production` for production deployment (default: `Development`)
- `DATABASE_URL` — PostgreSQL connection string (automatically set on Heroku)

You can also use `.env` instead of `.env.local`.  
Variables in `.env.local` will override those in `.env` if both exist.

## Running the App

Start the Flask server (the scheduler will run automatically in the background):

```bash
python app.py
```

The app will be available at [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

## Endpoints

### Health Check
- `GET /` — Returns API status and links to available tools

### Student Data
- `GET /get-student-data-from-record/<student_record>` — Get individual student data by record ID
- `GET /get-student-data-from-websiteId/<website_id>` — Get individual student data by website ID
- `GET /get-student-data-dashboard/<classroom_id>` — Get dashboard data for all students in a classroom
- `GET /update-student-current-step` — Update a student's current step (query params: websiteId, current-step)
- `GET /update-and-check-quest` — Update student's step and check for quest changes (query params: websiteId, current-step, allow-quest-update)

### Student Management
- `POST /add-students` — Add multiple students to the database with teacher assignment
- `DELETE /delete-students` — Delete multiple students by their website IDs
- `PUT /modify-students` — Modify student names (first_name, last_name) by website IDs
- `POST /assign-quests` — Assign quests to multiple students
- `POST /assign-quest-to-class` — Assign a quest to all students in a specific class
- `POST /assign-achievement-to-student` — Assign an achievement to a student

### Teacher Data  
- `GET /get-teacher-data/<id>` — Get teacher information by website user ID

### Quest and Step Data
- `GET /get-step-data` — Get step data (optional query param: step for specific step)

### Table Management
- `GET /get-table-as-csv/<table_name>` — Download table data as CSV
- `GET /get-table-as-json/<table_name>` — Get table data as JSON
- `GET /update-server-from-airtable` — Manually trigger update from Airtable for all tables
- `POST /update-table-from-airtable` — Update specific table from Airtable (supports force_delete option)

### Database Operations
- `POST /get-value-from-db` — Query specific values from database tables
- `POST /modify-field` — Update specific fields in database records

### Airtable Sync
- `POST /upload-to-airtable` — Upload modified data back to Airtable
- `GET /get-modified-tables` — List tables that have been modified locally

## Database

The application supports two database modes:

- **Development**: Uses SQLite with data stored in `data/airtable_data.db`
- **Production**: Uses PostgreSQL (automatically detected via `DATABASE_URL` environment variable)

Tables are automatically created and populated from Airtable data:
- `craffft_students` — Student information and progress
- `craffft_teachers` — Teacher and classroom data  
- `craffft_quests` — Educational quest definitions
- `craffft_steps` — Individual learning steps
- `craffft_responses` — Student responses and submissions
- `craffft_achievements` — Student achievements and rewards
- Additional curriculum and alignment tables

## Deployment

### Local Development
```bash
python app.py
```

## Running Tests

The project includes comprehensive tests for all API endpoints and functionality.

### Run All Tests
```bash
python tests.py
```

### Run Specific Tests
You can run individual test functions by importing and calling them:

```python
from tests import test_delete_students_api, test_modify_students_api
test_delete_students_api()
test_modify_students_api()
```

### Test Coverage
The test suite includes:
- **Database Operations**: Table management, CRUD operations, data validation
- **Student Management**: Add, delete, modify students with database verification
- **Quest Assignment**: Individual and class-wide quest assignments
- **Achievement System**: Student achievement assignment and tracking
- **API Endpoints**: All REST endpoints with success and error scenarios
- **Data Synchronization**: Airtable integration and upload functionality

### Test Environment
Tests automatically:
- Set up test data in the database
- Verify API responses and status codes
- Confirm database changes are persisted
- Clean up test data after completion

**Note**: Tests use the same database configuration as the main application, so ensure your environment variables are properly configured before running tests, and ensure you have a copy of the database locally

### Heroku Deployment
The app is configured for Heroku deployment with:
- `Procfile` for web process configuration
- `runtime.txt` for Python version specification
- Automatic PostgreSQL database detection
- Environment-based configuration

## Data Synchronization

The scheduler runs automatically and updates data from Airtable:
- **Production**: Daily at midnight + on startup
- **Development**: On-demand via API endpoints

This ensures the local database stays synchronized with the latest Airtable data.
