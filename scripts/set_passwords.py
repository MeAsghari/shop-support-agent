from getpass import getpass

from third_agent.auth import hash_password
from third_agent.database.queries import set_password_hash

for email in ["ali@example.com", "sara@example.com"]:
    password = getpass(f"Password for {email}: ")  # typing is hidden
    if len(password) < 8:
        print("  Too short (min 8 characters), skipped.")
        continue
    print("  saved:", set_password_hash(email, hash_password(password)))