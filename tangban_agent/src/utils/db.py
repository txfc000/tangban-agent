import os
import json

def get_user_data_path(username):
    return f"data/{username}/user_data.json"

def get_default_data():
    return {
        "profile": {
            "height": 170,
            "weight": 70,
            "age": 50,
            "gender": "男"
        },
        "preferences": {
            "likes": [],
            "dislikes": []
        },
        "recipes": [],
        "chat_history": []
    }

def load_user_data(username):
    path = get_user_data_path(username)
    default = get_default_data()
    if not os.path.exists(path):
        return default
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    for key in default:
        if key not in data:
            data[key] = default[key]
        elif isinstance(default[key], dict):
            for subkey in default[key]:
                if subkey not in data[key]:
                    data[key][subkey] = default[key][subkey]
    return data

def save_user_data(username, data):
    path = get_user_data_path(username)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)