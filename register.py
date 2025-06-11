import json
import uuid
import os
import sys
import argparse # Import the argparse module

# Define the path to the users.json file
# It assumes 'data' directory is relative to the script's location
USERS_FILE_PATH = os.path.join(os.path.dirname(__file__), 'data', 'users.json')
USERS_DIR_PATH = os.path.dirname(USERS_FILE_PATH)


def clear_screen():
    """Clears the console screen."""
    # For Windows
    if os.name == 'nt':
        _ = os.system('cls')
    # For macOS and Linux
    else:
        _ = os.system('clear')


def load_users():
    """Loads user data from users.json."""
    if not os.path.exists(USERS_FILE_PATH):
        # Ensure the data directory exists
        os.makedirs(USERS_DIR_PATH, exist_ok=True)
        return []
    with open(USERS_FILE_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            print(
                "警告: users.json 檔案損壞或為空。將從無用戶狀態開始。")  # Warning: users.json is malformed or empty. Starting with no users.
            return []  # Return empty list if JSON is malformed


def save_users(users):
    """Saves user data to users.json."""
    os.makedirs(USERS_DIR_PATH, exist_ok=True)  # Ensure directory exists before saving
    with open(USERS_FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(users, f, indent=4, ensure_ascii=False)


def generate_token():
    """Generates a unique authentication token."""
    return str(uuid.uuid4()).replace('-', '')


def register_user(username=None, password=None, permission_level=None, auto_login=False):
    """CLI tool to register a new user, with optional automatic input."""
    if username is None or password is None or permission_level is None:
        clear_screen()
        print("--- 用戶註冊 ---")  # --- User Registration ---
        username_input = input("輸入用戶名: ").strip()  # Enter username:
        password_input = input("輸入密碼: ").strip()  # Enter password:
        username = username_input if username is None else username
        password = password_input if password is None else password
    else:
        # If arguments are provided, print registration info without clearing screen
        print(f"--- 自動註冊用戶: {username} ---")

    users = load_users()

    # Check if username already exists
    if any(user['username'] == username for user in users):
        print(
            f"\n錯誤: 用戶名 '{username}' 已存在。請選擇另一個。")  # Error: Username '{username}' already exists. Please choose another.
        if not (username and password and permission_level): # Only prompt if not automated
            input("按 Enter 鍵繼續...")  # Press Enter to continue...
        return None  # Indicate registration failed

    # Choose permission level with numbered options if not provided
    if permission_level is None:
        while True:
            print("\n選擇您的權限等級:")  # Choose your permission level:
            print("1. Free: 免費方案")  # Free: Free tier
            print("2. Plus: NT$60 / 1 個月")  # Plus: NT$60 for 1 month
            print("3. Pro: NT$120 / 1 個月")  # Pro: NT$120 for 1 month
            choice = input("輸入您的選擇 (1, 2, 或 3): ").strip()  # Enter your choice (1, 2, or 3):

            if choice == '1':
                permission_level = 'free'
            elif choice == '2':
                permission_level = 'plus'
            elif choice == '3':
                permission_level = 'pro'
            else:
                print("無效的選擇。請選擇 1, 2, 或 3。")  # Invalid choice. Please choose 1, 2, or 3.
                continue  # Ask again
            break # Exit loop if a valid choice was made
    else:
        # Validate provided permission_level
        if permission_level.lower() not in ['free', 'plus', 'pro']:
            print(f"錯誤: 無效的權限等級 '{permission_level}'. 請使用 'free', 'plus', 或 'pro'.")
            if not (username and password and permission_level):
                input("按 Enter 鍵繼續...")
            return None
        permission_level = permission_level.lower()


    token = generate_token()

    new_user = {
        "username": username,
        "password": password,  # WARNING: In a real app, hash this password!
        "token": token,
        "permission_level": permission_level,
        "query_quota": 0  # This field exists but is not actively used in this CLI for now.
    }

    users.append(new_user)
    save_users(users)
    print("\n--- 註冊成功！ ---")  # --- Registration Successful! ---
    print(f"用戶名: {username}")  # Username:
    print(f"權限等級: {permission_level.upper()}")  # Permission Level:
    print(f"您的 API Token: {token}")  # Your API Token:
    print("---------------------------------")
    print("請記住您的 token 以便 API 訪問。")  # Remember your token for API access.

    if auto_login:
        print("自動登錄到新創建的帳戶...")
        return new_user # Return the newly created user for auto-login
    elif not (username and password and permission_level): # Only prompt if not automated
        input("按 Enter 鍵繼續...")  # Press Enter to continue...
    return new_user  # Indicate registration successful and return the user


def login_user(username=None, password=None):
    """CLI tool to log in an existing user, with optional automatic input."""
    if username is None or password is None:
        clear_screen()
        print("--- 用戶登錄 ---")  # --- User Login ---
        username_input = input("輸入用戶名: ").strip()  # Enter username:
        password_input = input("輸入密碼: ").strip()  # Enter password:
        username = username_input if username is None else username
        password = password_input if password is None else password
    else:
        print(f"--- 自動登錄用戶: {username} ---")


    users = load_users()
    logged_in_user = None

    for user in users:
        if user['username'] == username and user['password'] == password:
            logged_in_user = user
            break

    if logged_in_user:
        print(
            f"\n登錄成功！歡迎, {logged_in_user['username']}！")  # Login successful! Welcome, {logged_in_user['username']}!
        if not (username and password): # Only prompt if not automated
            input("按 Enter 鍵繼續...")  # Press Enter to continue...
        return logged_in_user
    else:
        print("\n錯誤: 無效的用戶名或密碼。")  # Error: Invalid username or password.
        if not (username and password): # Only prompt if not automated
            input("按 Enter 鍵繼續...")  # Press Enter to continue...
        return None


def edit_username(current_user):
    """Allows a logged-in user to change their username."""
    clear_screen()
    print("--- 編輯用戶名 ---")  # --- Edit Username ---
    new_username = input(
        f"輸入新用戶名 (目前: {current_user['username']}): ").strip()  # Enter new username (current: {current_user['username']}):

    if not new_username:
        print("用戶名不能為空。")  # Username cannot be empty.
        input("按 Enter 鍵繼續...")  # Press Enter to continue...
        return

    users = load_users()
    # Check if the new username already exists (excluding the current user's entry)
    if any(user['username'] == new_username for user in users if user['token'] != current_user['token']):
        print(
            f"錯誤: 用戶名 '{new_username}' 已被佔用。請選擇另一個。")  # Error: Username '{new_username}' already taken. Please choose another.
        input("按 Enter 鍵繼續...")  # Press Enter to continue...
        return

    # Find and update the user in the list
    for user in users:
        if user['token'] == current_user['token']:
            user['username'] = new_username
            break
    save_users(users)
    current_user['username'] = new_username  # Update the in-memory user object as well
    print(f"用戶名已成功更改為 '{new_username}'。")  # Username successfully changed to '{new_username}'.
    input("按 Enter 鍵繼續...")  # Press Enter to continue...


def edit_password(current_user):
    """Allows a logged-in user to change their password."""
    clear_screen()
    print("--- 編輯密碼 ---")  # --- Edit Password ---
    print(
        "警告: 為簡單起見，此範例中密碼未被雜湊。在實際應用中，務必雜湊密碼！")  # WARNING: For simplicity, passwords are NOT hashed in this example. In a real application, ALWAYS hash passwords!
    new_password = input("輸入新密碼: ").strip()  # Enter new password:

    if not new_password:
        print("密碼不能為空。")  # Password cannot be empty.
        input("按 Enter 鍵繼續...")  # Press Enter to continue...
        return

    users = load_users()
    # Find and update the user in the list
    for user in users:
        if user['token'] == current_user['token']:
            user['password'] = new_password
            break
    save_users(users)
    current_user['password'] = new_password  # Update the in-memory user object as well
    print("密碼已成功更改。")  # Password successfully changed.
    input("按 Enter 鍵繼續...")  # Press Enter to continue...


def upgrade_permission(current_user):
    """Allows a logged-in user to upgrade their permission level."""
    clear_screen()
    print("--- 升級權限 ---")  # --- Upgrade Permission ---
    print("目前權限等級: " + current_user['permission_level'].upper())  # Current Permission Level:
    print("\n--- 權益表 ---")  # --- Benefit Table ---
    print(
        "- Free: 每 6 秒查詢，每分鐘限制 15 次請求，每次生成 1 筆航班。")  # Query every 6 seconds, 15 requests/minute, generates 1 flight per query.
    print(
        "- Plus: 每 4 秒查詢，每分鐘限制 25 次請求，每次生成 2 筆航班。")  # Query every 4 seconds, 25 requests/minute, generates 2 flights per query.
    print(
        "- Pro: 每 2 秒查詢，每分鐘限制 100 次請求，每次生成 3 筆航班，模擬高頻查詢情境。")  # Query every 2 seconds, 100 requests/minute, generates 3 flights per query, simulates high-frequency queries.
    print("---------------------\n")

    current_level = current_user['permission_level']

    if current_level == 'free':
        print("升級選項:")  # Upgrade Options:
        print("1. 升級到 Plus: NT$60 / 1 個月")  # Upgrade to Plus: NT$60 for 1 month
        print("2. 升級到 Pro: NT$120 / 1 個月")  # Upgrade to Pro: NT$120 for 1 month
        choice = input("輸入您的選擇 (1/2 或 'b' 返回): ").strip().lower()  # Enter your choice (1/2 or 'b' to go back):
        if choice == '1':
            new_level = 'plus'
        elif choice == '2':
            new_level = 'pro'
        elif choice == 'b':
            return
        else:
            print("無效的選擇。")  # Invalid choice.
            input("按 Enter 鍵繼續...")  # Press Enter to continue...
            return
    elif current_level == 'plus':
        print("升級選項:")  # Upgrade Options:
        print("1. 升級到 Pro: NT$60 / 1 個月")  # Upgrade to Pro: NT$60 for 1 month
        choice = input("輸入您的選擇 (1 或 'b' 返回): ").strip().lower()  # Enter your choice (1 or 'b' to go back):
        if choice == '1':
            new_level = 'pro'
        elif choice == 'b':
            return
        else:
            print("無效的選擇。")  # Invalid choice.
            input("按 Enter 鍵繼續...")  # Press Enter to continue...
            return
    elif current_level == 'pro':
        print("您目前的權限等級已是最高 (Pro)。")  # You're current permission level is the highest (Pro).
        input("按 Enter 鍵繼續...")  # Press Enter to continue...
        return
    else: # Should not happen with current logic, but good for robustness
        print("未知權限等級。")
        input("按 Enter 鍵繼續...")
        return


    # Simulate payment confirmation
    confirm = input(
        f"確認升級到 {new_level.upper()}？ (yes/no): ").strip().lower()  # Confirm upgrade to {new_level.upper()}? (yes/no):
    if confirm == 'yes':
        users = load_users()
        for user in users:
            if user['token'] == current_user['token']:
                user['permission_level'] = new_level
                break
        save_users(users)
        current_user['permission_level'] = new_level  # Update in-memory
        print(f"\n已成功升級到 {new_level.upper()}！")  # Successfully upgraded to {new_level.upper()}!
        input("按 Enter 鍵繼續...")  # Press Enter to continue...
    else:
        print("升級已取消。")  # Upgrade cancelled.
        input("按 Enter 鍵繼續...")  # Press Enter to continue...


def view_token(current_user):
    """Displays the current user's API token."""
    clear_screen()
    print("--- 查看 API Token ---")  # --- View API Token ---
    print(f"您的 API Token: {current_user['token']}")  # Your API Token:
    print("----------------------")
    print("請妥善保管此 token！不要公開分享。")  # Keep this token secure! Do not share it publicly.
    input("按 Enter 鍵繼續...")  # Press Enter to continue...


def account_menu(logged_in_user):
    """Displays the account management menu for a logged-in user."""
    while True:
        clear_screen()
        print(
            f"--- 歡迎, {logged_in_user['username']}！ (權限: {logged_in_user['permission_level'].upper()}) ---")  # --- Welcome, {logged_in_user['username']}! (Permission: {logged_in_user['permission_level'].upper()}) ---
        print("1. 編輯用戶名")  # Edit Username
        print("2. 編輯密碼")  # Edit Password
        print("3. 升級權限")  # Upgrade Permission
        print("4. 查看 API Token")  # View API Token
        print("5. 登出")  # Logout
        choice = input("輸入您的選擇: ").strip()  # Enter your choice:

        if choice == '1':
            edit_username(logged_in_user)
        elif choice == '2':
            edit_password(logged_in_user)
        elif choice == '3':
            upgrade_permission(logged_in_user)
        elif choice == '4':
            view_token(logged_in_user)
        elif choice == '5':
            print("正在登出...")  # Logging out...
            input("按 Enter 鍵繼續...")  # Press Enter to continue...
            break
        else:
            print("無效的選擇。請重試。")  # Invalid choice. Please try again.
            input("按 Enter 鍵繼續...")  # Press Enter to continue...


def main_lobby():
    """Main function to run the CLI lobby."""
    while True:
        clear_screen()
        print("--- 歡迎來到大廳！ ---")  # --- Welcome to the Lobby! ---
        print("1. 創建帳戶")  # Create Account
        print("2. 登錄帳戶")  # Login to Account
        print("3. 退出")  # Exit
        choice = input("輸入您的選擇: ").strip()  # Enter your choice:

        if choice == '1':
            register_user()
        elif choice == '2':
            user = login_user()
            if user:
                account_menu(user)
        elif choice == '3':
            print("正在退出大廳。再見！")  # Exiting Lobby. Goodbye!
            sys.exit()  # Use sys.exit() to properly terminate
        else:
            print("無效的選擇。請重試。")  # Invalid choice. Please try again.
            input("按 Enter 鍵繼續...")  # Press Enter to continue...


if __name__ == "__main__":
    # Custom formatter to display help messages more clearly
    class CustomHelpFormatter(argparse.HelpFormatter):
        def _format_action_invocation(self, action):
            if not action.option_strings:
                return super()._format_action_invocation(action)
            default_format = super()._format_action_invocation(action)
            # Remove the default metavar which is often redundant or confusing
            if action.nargs == '*' and action.metavar is None:
                return default_format.replace(' []', '')
            return default_format

        def _format_usage(self, usage, actions, groups, prefix):
            # Customize the usage string to explicitly list the commands
            return f"""用法: python register.py [選項]

可用命令:
  1. python register.py                   : 正常運行，進入主大廳。
  2. python register.py -c                : 進入互動式創建帳戶模式。
  3. python register.py -c [用戶名] [密碼] [權限等級] : 自動創建帳戶，權限等級可選 'free', 'plus', 'pro'。
  4. python register.py -c [用戶名] [密碼] [權限等級] --autologin : 自動創建帳戶並登錄。
  5. python register.py -s                : 進入互動式登錄帳戶模式。
  6. python register.py -s [用戶名] [密碼] : 使用指定用戶名和密碼自動登錄帳戶。

"""

    parser = argparse.ArgumentParser(
        description="用戶管理 CLI 工具，支援帳戶創建、登錄與管理功能。",
        formatter_class=CustomHelpFormatter # Use the custom formatter
    )
    parser.add_argument('-c', '--create', nargs='*',
                        help="創建帳戶。使用 '--create' 進入互動模式，或 '--create [用戶名] [密碼] [權限等級]' 自動創建。")
    parser.add_argument('-s', '--signin', nargs='*',
                        help="登錄帳戶。使用 '--signin' 進入互動模式，或 '--signin [用戶名] [密碼]' 自動登錄。")
    parser.add_argument('--autologin', action='store_true',
                        help="與 '-c' (自動創建帳戶) 結合使用時，在創建成功後自動登錄到新創建的帳戶。")

    args = parser.parse_args()

    if args.create is not None:
        if len(args.create) == 0:  # -c
            register_user()
        elif len(args.create) == 3:  # -c [username] [password] [permission_level]
            username, password, permission_level = args.create
            new_user = register_user(username, password, permission_level, auto_login=args.autologin)
            if new_user and args.autologin:
                account_menu(new_user)
        else:
            print("創建帳戶的參數無效。請使用 '-c' 或 '-c [用戶名] [密碼] [權限等級]'。")
    elif args.signin is not None:
        if len(args.signin) == 0:  # -s
            user = login_user()
            if user:
                account_menu(user)
        elif len(args.signin) == 2:  # -s [username] [password]
            username, password = args.signin
            user = login_user(username, password)
            if user:
                account_menu(user)
        else:
            print("登錄帳戶的參數無效。請使用 '-s' 或 '-s [用戶名] [密碼]'。")
    else:
        main_lobby()
