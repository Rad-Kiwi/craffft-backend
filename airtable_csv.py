import os
from airtable import Airtable
import csv
import io
import json

class AirtableCSVManager:
    def __init__(self, base_id, table_name, api_key):
        self.base_id = base_id
        self.table_name = table_name
        self.api_key = api_key
        self.csv_path = "data/coastline-tiles-with-data.csv"


    def read_csv(self):
        # Read and return the raw CSV data from the file
        if not os.path.exists(self.csv_path):
            return None
        with open(self.csv_path, "r", encoding="utf-8") as f:
            return f.read()

    # Fetch CSV data from Airtable and save it to file
    def update_csv_from_airtable(self):
        airtable = Airtable(self.base_id, self.table_name, self.api_key)
        records = airtable.get_all()
        if not records:
            return None

        fieldnames = set()
        for record in records:
            fieldnames.update(record['fields'].keys())
        fieldnames = list(fieldnames)

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames)
        writer.writeheader()
        for record in records:
            writer.writerow(record['fields'])

        csv_data = output.getvalue()
        output.close()

        with open(self.csv_path, "w", encoding="utf-8") as f:
            f.write(csv_data)

        return "Successfully updated CSV from Airtable. Access it at /data/coastline-tiles-with-data.csv"

    def convert_csv_to_json(self):
        # Read the CSV file and convert to JSON, merging images fields
        if not os.path.exists(self.csv_path):
            return None
        result = []
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Merge imageUrls/* or images/* keys into a single 'images' array
                images = []
                keys_to_remove = []
                for k in list(row.keys()):
                    if k.startswith('images/') or k.startswith('imageUrls/'):
                        if row[k]:
                            images.append(row[k])
                        keys_to_remove.append(k)
                for k in keys_to_remove:
                    del row[k]
                if images:
                    row['images'] = images
                result.append(row)
        return result
