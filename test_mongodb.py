"""
Test MongoDB connection and collections
"""
from pymongo import MongoClient
import datetime

# Connect to MongoDB
client = MongoClient('localhost', 27017)
db = client.flask_db

# Test collections
collections = {
    "chat_post_task": db.chat_post_task,
    "chat_history_collection": db.chat_history,
    "chat_client_info": db.chat_client_info,
    "chat_in_task": db.chat_in_task,
    "chat_pre_task": db.chat_pre_task,
    "summative_writing": db.summative_writing,
    "summative_scoring": db.summative_scoring,
    "participants": db.participants  # New collection for treatment assignment
}

print("✓ MongoDB connection successful!")
print(f"✓ Available databases: {client.list_database_names()}")
print(f"✓ Collections configured: {len(collections)}")

# Test insert and retrieve
test_data = {
    "test_id": "test_001",
    "timestamp": datetime.datetime.now(datetime.timezone.utc),
    "message": "Test document"
}

print("\n--- Testing insert/retrieve ---")
result = db.test_collection.insert_one(test_data)
print(f"✓ Insert successful! ID: {result.inserted_id}")

retrieved = db.test_collection.find_one({"test_id": "test_001"})
print(f"✓ Retrieved: {retrieved['message']}")

# Clean up test
db.test_collection.delete_one({"test_id": "test_001"})
print("✓ Test document cleaned up")

print("\n--- All MongoDB tests passed! ---")
print(f"\nDatabase 'flask_db' collections:")
for coll_name in db.list_collection_names():
    count = db[coll_name].count_documents({})
    print(f"  - {coll_name}: {count} documents")
