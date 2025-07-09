import os
from typing import Optional
from datetime import datetime
from sqlalchemy import create_engine, Column, String, Text, DateTime
from sqlalchemy.orm import declarative_base, sessionmaker

Base = declarative_base()

class TableData(Base):
    __tablename__ = 'table_data'
    table_name = Column(String, primary_key=True)
    csv_data = Column(Text)
    json_data = Column(Text)
    updated_at = Column(DateTime, default=datetime.utcnow)

class SQLiteStorage:
    def __init__(self, db_path: str = "data/airtable_data.db"):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.db_path = db_path
        self.engine = create_engine(f'sqlite:///{db_path}', echo=False, future=True)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine, future=True)

    def save_csv(self, table_name: str, csv_data: str):
        with self.Session() as session:
            obj = session.get(TableData, table_name)
            if obj:
                obj.csv_data = csv_data
                obj.updated_at = datetime.utcnow()
            else:
                obj = TableData(table_name=table_name, csv_data=csv_data, updated_at=datetime.utcnow())
                session.add(obj)
            session.commit()

    def save_json(self, table_name: str, json_data: str):
        with self.Session() as session:
            obj = session.get(TableData, table_name)
            if obj:
                obj.json_data = json_data
                obj.updated_at = datetime.utcnow()
            else:
                obj = TableData(table_name=table_name, json_data=json_data, updated_at=datetime.utcnow())
                session.add(obj)
            session.commit()

    def get_csv(self, table_name: str) -> Optional[str]:
        with self.Session() as session:
            obj = session.get(TableData, table_name)
            return obj.csv_data if obj else None

    def get_json(self, table_name: str) -> Optional[str]:
        with self.Session() as session:
            obj = session.get(TableData, table_name)
            return obj.json_data if obj else None
