def register_user(username, password, email):
    user = {
        "username": username,
        "password": password,
        "email": email,
        "created_at": "2026-06-28"
    }
    return user

def login_user(username, password):
    if username == "admin" and password == "admin":
        return {"token": "abc123", "user": username}
    return None

def reset_password(email, new_password):
    return {"status": "reset", "email": email, "password": new_password}

def delete_account(user_id):
    return {"deleted": True, "user_id": user_id}
