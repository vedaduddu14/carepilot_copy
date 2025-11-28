"""
Simple JSON file-based database replacement for MongoDB
Stores data in JSON files instead of requiring MongoDB installation
"""
import json
import os
from datetime import datetime
from pathlib import Path

class JSONCollection:
    """Mimics MongoDB collection interface using JSON files"""

    def __init__(self, db_dir, collection_name):
        self.db_dir = Path(db_dir)
        self.collection_name = collection_name
        self.file_path = self.db_dir / f"{collection_name}.json"

        # Create directory if it doesn't exist
        self.db_dir.mkdir(parents=True, exist_ok=True)

        # Initialize file if it doesn't exist
        if not self.file_path.exists():
            self._write_data([])

    def _read_data(self):
        """Read all documents from JSON file"""
        try:
            with open(self.file_path, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return []

    def _write_data(self, data):
        """Write all documents to JSON file"""
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2, default=str)

    def insert_one(self, document):
        """Insert a single document"""
        data = self._read_data()
        # Add timestamp if not present
        if 'created_at' not in document:
            document['created_at'] = datetime.now().isoformat()
        data.append(document)
        self._write_data(data)
        return type('InsertResult', (), {'inserted_id': len(data) - 1})()

    def find_one(self, query=None):
        """Find a single document matching the query"""
        data = self._read_data()
        if query is None:
            return data[0] if data else None

        for doc in data:
            if all(doc.get(k) == v for k, v in query.items()):
                return doc
        return None

    def find(self, query=None):
        """Find all documents matching the query"""
        data = self._read_data()
        if query is None:
            return data

        results = []
        for doc in data:
            if all(doc.get(k) == v for k, v in query.items()):
                results.append(doc)
        return results

    def update_one(self, query, update):
        """Update a single document"""
        data = self._read_data()
        for i, doc in enumerate(data):
            if all(doc.get(k) == v for k, v in query.items()):
                # Handle $set operator
                if '$set' in update:
                    doc.update(update['$set'])
                else:
                    doc.update(update)
                doc['updated_at'] = datetime.now().isoformat()
                data[i] = doc
                self._write_data(data)
                return type('UpdateResult', (), {'modified_count': 1})()
        return type('UpdateResult', (), {'modified_count': 0})()

    def delete_many(self, query):
        """Delete all documents matching the query"""
        data = self._read_data()
        original_count = len(data)

        if query == {}:
            # Delete all
            self._write_data([])
            return type('DeleteResult', (), {'deleted_count': original_count})()

        # Filter out matching documents
        filtered_data = []
        for doc in data:
            if not all(doc.get(k) == v for k, v in query.items()):
                filtered_data.append(doc)

        self._write_data(filtered_data)
        deleted_count = original_count - len(filtered_data)
        return type('DeleteResult', (), {'deleted_count': deleted_count})()

    def count_documents(self, query=None):
        """Count documents matching the query"""
        if query is None or query == {}:
            return len(self._read_data())

        data = self._read_data()
        count = 0
        for doc in data:
            if all(doc.get(k) == v for k, v in query.items()):
                count += 1
        return count


class JSONDatabase:
    """Mimics MongoDB database interface"""

    def __init__(self, db_dir='data'):
        self.db_dir = db_dir
        self._collections = {}

    def __getattr__(self, name):
        """Get or create a collection"""
        if name not in self._collections:
            self._collections[name] = JSONCollection(self.db_dir, name)
        return self._collections[name]


class JSONClient:
    """Mimics MongoDB client interface"""

    def __init__(self, host='localhost', port=27017, db_dir='data'):
        self.host = host
        self.port = port
        self.db_dir = db_dir
        self._databases = {}

    def __getattr__(self, name):
        """Get or create a database"""
        if name not in self._databases:
            self._databases[name] = JSONDatabase(self.db_dir)
        return self._databases[name]
