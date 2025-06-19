# kelp-helpers-backend
This is the backend for the kelp helpers website

Its main task currently is to grab data from airtable.

It does this both once on the backend startup, and once daily at midnight.

If there are issues accessing airtable, currently the data is also stored on github as a backup, although this may be removed later if there are too many updates.


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
AIRTABLE_TABLE_NAME=your_table_name
AIRTABLE_API_KEY=your_airtable_api_key
```

You can also use `.env` instead of `.env.local`.  
Variables in `.env.local` will override those in `.env` if both exist.

## Running the App

Start the Flask server (the scheduler will run automatically in the background):

```bash
python app.py
```

The app will be available at [http://127.0.0.1:5000/](http://127.0.0.1:5000/).

## Endpoints

- `/` — Health check, returns "Hello, Flask!"
- `/airtable-csv` — Returns Airtable data as JSON.
- `/save-airtable-csv` — Saves Airtable data as CSV to `data/coastline-tiles-with-data.csv`.

## Scheduler

The scheduler runs automatically when you start the app and updates the CSV file daily at midnight.
