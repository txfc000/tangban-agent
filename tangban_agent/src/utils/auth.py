import hashlib
import os
import json

USER_DB = "data/users.json"

def get_users():
    if not os.path.exists(USER_DB):
        return {}
    with open(USER_DB, "r", encoding="utf-8") as f:
        return json.load(f)

def save_users(users):
    os.makedirs("data", exist_ok=True)
    with open(USER_DB, "w", encoding="utf-8") as f:
        json.dump(users, f, indent=2)

def hash_password(password, salt=None):
    if salt is None:
        salt = os.urandom(16).hex()
    hash_obj = hashlib.sha256((salt + password).encode())
    return salt, hash_obj.hexdigest()

def register(username, password):
    users = get_users()
    if username in users:
        return False, "用户名已存在"
    salt, pwd_hash = hash_password(password)
    users[username] = {"salt": salt, "password_hash": pwd_hash}
    save_users(users)
    os.makedirs(f"data/{username}", exist_ok=True)
    return True, "注册成功"

def login(username, password):
    users = get_users()
    if username not in users:
        return False, "用户名不存在"
    user = users[username]
    _, calc_hash = hash_password(password, user["salt"])
    if calc_hash == user["password_hash"]:
        return True, "登录成功"
    return False, "密码错误"