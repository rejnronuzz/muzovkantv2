import json
import os

DATA_FILE = 'data/role_message_id.json'

def save_message_id(message_id):
    os.makedirs('data', exist_ok=True)
    with open(DATA_FILE, 'w') as f:
        json.dump({'message_id': message_id}, f)

def load_message_id():
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        return data.get('message_id')
    except FileNotFoundError:
        return None
    except json.JSONDecodeError:
        return None