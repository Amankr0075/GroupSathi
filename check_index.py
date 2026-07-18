from pymongo import MongoClient

client = MongoClient("mongodb+srv://amankumar3432k_db_user:Aman62478140@cluster0.8edue7r.mongodb.net/groupsathi_db?retryWrites=true&w=majority&appName=Cluster0")
db = client['groupsathi_db']
print(db.users.index_information())
