import json
import uuid
import os

# Define the path to the users.json file
# If register.py is in the root, it needs to go INTO 'data'
USERS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
USERS_DIR_PATH = os.path.dirname(USERS_FILE_PATH)

def load_users():
    """Loads user data from users.json."""
    if not os.path.exists(USERS_FILE_PATH):
        return []
    with open(USERS_FILE_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return [] # Return empty list if JSON is malformed

def save_users(users):
    """Saves user data to users.json."""
    with open(USERS_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)

def generate_token():
    """Generates a unique authentication token."""
    return str(uuid.uuid4()).replace('-', '')

def register_user():
    """CLI tool to register a new user."""
    print("--- User Registration ---")
    username = input("Enter username: ").strip()
    password = input("Enter password: ").strip()

    users = load_users()

    # Check if username already exists
    if any(user['username'] == username for user in users):
        print(f"Error: Username '{username}' already exists. Please choose another.")
        return

    # Choose permission level
    while True:
        permission_level = input("Enter permission level (free/plus/pro): ").strip().lower()
        if permission_level in ['free', 'plus', 'pro']:
            break
        else:
            print("Invalid permission level. Please choose 'free', 'plus', or 'pro'.")

    token = generate_token()


    new_user = {
        "username": username,
        "password": password, # In a real app, hash this!
        "token": token,
        "permission_level": permission_level,
        "query_quota": 0
    }

    users.append(new_user)
    save_users(users)
    print("\n--- Registration Successful! ---")
    print(f"Username: {username}")
    print(f"Permission Level: {permission_level}")
    print(f"Your API Token: {token}")
    print("---------------------------------")
    print("Remember your token for API access.")

if __name__ == "__main__":
    register_user()