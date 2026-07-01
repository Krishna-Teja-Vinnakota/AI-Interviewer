import os
from pymongo import MongoClient
from dotenv import load_dotenv

# Load environment variables from backend/.env
env_path = os.path.join(os.path.dirname(__file__), 'backend', '.env')
load_dotenv(env_path)

def get_mongo_client():
    """Get MongoDB client using URI from .env file"""
    mongodb_uri = os.getenv('MONGODB_URI')
    if not mongodb_uri:
        raise ValueError("MONGODB_URI not found in .env file")
    return MongoClient(mongodb_uri)

def list_collections(db):
    """List all collections in the database"""
    collections = db.list_collection_names()
    return collections

def delete_collections_except(db, keep_collections):
    """Delete all collections except the ones specified"""
    all_collections = list_collections(db)
    collections_to_delete = [col for col in all_collections if col not in keep_collections]
    
    if not collections_to_delete:
        print("\nNo collections to delete.")
        return
    
    print(f"\nCollections to be deleted: {', '.join(collections_to_delete)}")
    confirm = input("Are you sure you want to delete these collections? (yes/no): ").strip().lower()
    
    if confirm == 'yes':
        for collection_name in collections_to_delete:
            db.drop_collection(collection_name)
            print(f"✓ Deleted collection: {collection_name}")
        print(f"\nSuccessfully deleted {len(collections_to_delete)} collection(s).")
    else:
        print("Operation cancelled.")

def main():
    try:
        # Connect to MongoDB
        client = get_mongo_client()
        db_name = os.getenv('MONGODB_DATABASE_NAME', 'ai_interviewer')
        db = client[db_name]
        
        print(f"Connected to MongoDB database: {db_name}")
        print("=" * 60)
        
        # List all collections
        collections = list_collections(db)
        
        if not collections:
            print("No collections found in the database.")
            return
        
        print(f"\nAvailable collections ({len(collections)}):")
        for idx, collection in enumerate(collections, 1):
            doc_count = db[collection].count_documents({})
            print(f"{idx}. {collection} ({doc_count} documents)")
        
        print("\n" + "=" * 60)
        print("Enter the collection numbers you want to KEEP (comma-separated)")
        print("Example: 1,3,5 (will delete all except collections 1, 3, and 5)")
        print("=" * 60)
        
        # Get user input
        user_input = input("\nCollections to keep (numbers): ").strip()
        
        if not user_input:
            print("No input provided. Exiting.")
            return
        
        # Parse user input
        try:
            keep_indices = [int(x.strip()) for x in user_input.split(',')]
        except ValueError:
            print("Invalid input. Please enter numbers separated by commas.")
            return
        
        # Validate indices
        invalid_indices = [idx for idx in keep_indices if idx < 1 or idx > len(collections)]
        if invalid_indices:
            print(f"Invalid collection numbers: {', '.join(map(str, invalid_indices))}")
            return
        
        # Get collection names to keep
        keep_collections = [collections[idx - 1] for idx in keep_indices]
        
        print(f"\nCollections to KEEP: {', '.join(keep_collections)}")
        
        # Delete collections except the ones to keep
        delete_collections_except(db, keep_collections)
        
    except Exception as e:
        print(f"Error: {str(e)}")
    finally:
        if 'client' in locals():
            client.close()
            print("\nMongoDB connection closed.")

if __name__ == "__main__":
    main()
