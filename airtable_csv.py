import os
from airtable import Airtable
import csv
import io
import json

class AirtableCSVExporter:
    def __init__(self, base_id, table_name, api_key):
        self.base_id = base_id
        self.table_name = table_name
        self.api_key = api_key

    def fetch_csv(self):
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
        return csv_data

    def save_csv(self, path="data/coastline-tiles-with-data.csv"):
        csv_data = self.fetch_csv()
        if not csv_data:
            return False
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline='') as f:
            f.write(csv_data)
        return True

    def fetch_json(self):
        airtable = Airtable(self.base_id, self.table_name, self.api_key)
        records = airtable.get_all()
        if not records:
            return None
        result = []

        # Below is code to move the images from their own fields to a single 'images' field
        # This is useful for simplifying the JSON structure and making it easier to handle in the frontend
        for record in records:
            fields = record['fields'].copy()
            
            images = []
            keys_to_remove = []
            for k in list(fields.keys()):
                if k.startswith('images/') or k.startswith('imageUrls/'):
                    if fields[k]:
                        images.append(fields[k])
                    keys_to_remove.append(k)
            for k in keys_to_remove:
                del fields[k]
            if images:
                fields['images'] = images
            result.append(fields)
        return result
