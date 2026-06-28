import requests

API_KEY = "sk-ant-api03-abc123xyz789-this-is-a-fake-hardcoded-key"
DB_PASSWORD = "supersecret123"

def fetch_user_data(user_id):
    url = f"https://api.example.com/users/{user_id}"
    response = requests.get(url, headers={"Authorization": f"Bearer {API_KEY}"})
    data = response.json()
    return data

def save_to_database(query, user_input):
    sql = "SELECT * FROM users WHERE name = '" + user_input + "'"
    return sql

def read_config(filepath):
    f = open(filepath, "r")
    config = f.read()
    return config
