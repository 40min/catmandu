#!/usr/bin/env python3
"""
Helper script to manage Notion user configurations in .env file.
This script helps add, remove, and list Notion user configurations.
"""

import argparse
import re
import sys
from pathlib import Path

# Add src to path for imports when testing
sys.path.insert(0, str(Path(__file__).parent.parent / "cattackles" / "notion" / "src"))


def get_env_file_path():
    """Get the path to the .env file."""
    return Path(__file__).parent.parent / ".env"


def read_env_file():
    """Read the .env file and return its contents as lines."""
    env_file = get_env_file_path()
    if not env_file.exists():
        return []

    with open(env_file, "r") as f:
        return f.readlines()


def write_env_file(lines):
    """Write lines to the .env file."""
    env_file = get_env_file_path()
    with open(env_file, "w") as f:
        f.writelines(lines)


def normalize_username(username):
    """Convert username to environment variable format (uppercase with underscores)."""
    # Replace spaces and hyphens with underscores, convert to uppercase
    normalized = re.sub(r"[^a-zA-Z0-9_]", "_", username.upper())
    # Remove multiple consecutive underscores
    normalized = re.sub(r"_+", "_", normalized)
    # Remove leading/trailing underscores
    normalized = normalized.strip("_")
    return normalized


def find_user_lines(lines, username):
    """Find lines in .env that belong to a specific user."""
    env_username = normalize_username(username)
    token_pattern = f"NOTION__USER__{env_username}__TOKEN="
    page_pattern = f"NOTION__USER__{env_username}__PARENT_PAGE_ID="

    user_lines = []
    for i, line in enumerate(lines):
        if line.strip().startswith(token_pattern) or line.strip().startswith(page_pattern):
            user_lines.append(i)

    return user_lines


def add_user(username, token, parent_page_id):
    """Add a new user configuration to .env file."""
    env_username = normalize_username(username)

    lines = read_env_file()

    # Check if user already exists
    existing_lines = find_user_lines(lines, username)
    if existing_lines:
        print(f"❌ User '{username}' already exists in .env file")
        print("   Use 'update' command to modify existing configuration")
        return False

    # Find the Notion section or create it
    notion_section_start = -1
    for i, line in enumerate(lines):
        if "NOTION CATTACKLE CONFIGURATION" in line:
            notion_section_start = i
            break

    if notion_section_start == -1:
        # Add Notion section at the end
        if lines and not lines[-1].endswith("\n"):
            lines.append("\n")
        lines.extend(
            [
                "\n",
                "# =============================================================================\n",
                "# NOTION CATTACKLE CONFIGURATION\n",
                "# =============================================================================\n",
                "\n",
            ]
        )
        notion_section_start = len(lines) - 5

    # Add user configuration after the section header
    insert_pos = notion_section_start + 5  # After the header comments

    # Find a good insertion point (after existing users or section header)
    while insert_pos < len(lines) and (
        lines[insert_pos].strip().startswith("#")
        or lines[insert_pos].strip().startswith("NOTION__USER__")
        or lines[insert_pos].strip() == ""
    ):
        insert_pos += 1

    # Insert new user configuration
    new_lines = [
        f"# User: {username}\n",
        f"NOTION__USER__{env_username}__TOKEN={token}\n",
        f"NOTION__USER__{env_username}__PARENT_PAGE_ID={parent_page_id}\n",
        "\n",
    ]

    for i, new_line in enumerate(new_lines):
        lines.insert(insert_pos + i, new_line)

    write_env_file(lines)
    print(f"✅ Added user '{username}' to .env file")
    print("   Environment variables:")
    print(f"   - NOTION__USER__{env_username}__TOKEN")
    print(f"   - NOTION__USER__{env_username}__PARENT_PAGE_ID")
    return True


def remove_user(username):
    """Remove a user configuration from .env file."""
    lines = read_env_file()
    user_lines = find_user_lines(lines, username)

    if not user_lines:
        print(f"❌ User '{username}' not found in .env file")
        return False

    # Remove lines in reverse order to maintain indices
    for line_idx in reversed(user_lines):
        # Also remove the comment line before if it's a user comment
        if line_idx > 0 and lines[line_idx - 1].strip().startswith(f"# User: {username}"):
            lines.pop(line_idx - 1)
            line_idx -= 1
        lines.pop(line_idx)

    write_env_file(lines)
    print(f"✅ Removed user '{username}' from .env file")
    return True


def list_users():
    """List all configured Notion users."""
    lines = read_env_file()

    users = {}
    pattern = re.compile(r"^NOTION__USER__([A-Z0-9_]+)__(TOKEN|PARENT_PAGE_ID)=(.*)$")

    for line in lines:
        match = pattern.match(line.strip())
        if match:
            env_username = match.group(1)
            field = match.group(2).lower()
            value = match.group(3)

            # Convert back to readable username
            username = env_username.lower().replace("_", " ").title()

            if username not in users:
                users[username] = {}

            users[username][field] = value

    if not users:
        print("❌ No Notion users configured in .env file")
        print("\nTo add a user, run:")
        print("   python scripts/manage_notion_users.py add <username> <token> <parent_page_id>")
        return

    print(f"✅ Found {len(users)} configured Notion user(s):")
    print()

    for username, config in users.items():
        print(f"👤 {username}")
        token = config.get("token", "MISSING")
        page_id = config.get("parent_page_id", "MISSING")

        if token and token != "MISSING":
            print(f"   Token: {token[:10]}...{token[-4:] if len(token) > 14 else ''}")
        else:
            print(f"   Token: ❌ {token}")

        print(f"   Parent Page ID: {page_id}")

        # Check if configuration is complete
        if token and token != "MISSING" and page_id and page_id != "MISSING":
            print("   Status: ✅ Complete")
        else:
            print("   Status: ❌ Incomplete")
        print()


def update_user(username, token=None, parent_page_id=None):
    """Update an existing user configuration."""
    lines = read_env_file()
    user_lines = find_user_lines(lines, username)

    if not user_lines:
        print(f"❌ User '{username}' not found in .env file")
        print("   Use 'add' command to create a new user")
        return False

    env_username = normalize_username(username)
    updated = False

    # Update existing lines
    for line_idx in user_lines:
        line = lines[line_idx]

        if token and f"NOTION__USER__{env_username}__TOKEN=" in line:
            lines[line_idx] = f"NOTION__USER__{env_username}__TOKEN={token}\n"
            updated = True
            print(f"✅ Updated token for user '{username}'")

        if parent_page_id and f"NOTION__USER__{env_username}__PARENT_PAGE_ID=" in line:
            lines[line_idx] = f"NOTION__USER__{env_username}__PARENT_PAGE_ID={parent_page_id}\n"
            updated = True
            print(f"✅ Updated parent page ID for user '{username}'")

    if updated:
        write_env_file(lines)
        return True
    else:
        print(f"❌ No updates specified for user '{username}'")
        return False


def test_user_config(username: str) -> bool:
    """Test configuration for a specific user."""
    try:
        # Load environment variables from .env file
        from dotenv import load_dotenv

        load_dotenv()

        from notion.config.user_config import get_user_config, is_user_authorized
    except ImportError:
        print("❌ Cannot import Notion configuration modules")
        print("   Make sure you're running this from the project root and Notion cattackle is properly installed")
        return False

    print(f"🔍 Testing configuration for user: {username}")

    config = get_user_config(username)

    if config:
        print(f"✅ Configuration found for {username}")

        # Show token (masked for security)
        token = config.get("token", "MISSING")
        if token and token != "MISSING":
            print(f"   Token: {token[:10]}...{token[-4:] if len(token) > 14 else ''}")
        else:
            print("   Token: ❌ MISSING")

        # Show parent page ID
        parent_page_id = config.get("parent_page_id", "MISSING")
        print(f"   Parent Page ID: {parent_page_id}")

        # Check authorization
        if is_user_authorized(username):
            print(f"✅ User {username} is fully authorized")
            return True
        else:
            print(f"❌ User {username} has incomplete configuration")
            return False
    else:
        print(f"❌ No configuration found for {username}")
        print("   Make sure you have set the environment variables:")
        env_username = normalize_username(username)
        print(f"   NOTION__USER__{env_username}__TOKEN")
        print(f"   NOTION__USER__{env_username}__PARENT_PAGE_ID")
        return False


def test_all_configs():
    """Test all discovered user configurations."""
    try:
        # Load environment variables from .env file
        from dotenv import load_dotenv

        load_dotenv()

        from notion.config.user_config import _get_user_configs
    except ImportError:
        print("❌ Cannot import Notion configuration modules")
        print("   Make sure you're running this from the project root and Notion cattackle is properly installed")
        return False

    print("🔍 Discovering all user configurations...")

    user_configs = _get_user_configs()

    if not user_configs:
        print("❌ No user configurations found in environment variables")
        print("\nTo add a user configuration, use this script:")
        print("   python scripts/manage_notion_users.py add <username> <token> <parent_page_id>")
        print("\nExample:")
        print("   python scripts/manage_notion_users.py add 'John Doe' 'secret_token_123' 'page_id_456'")
        return False

    print(f"✅ Found {len(user_configs)} user configuration(s)")
    print()

    all_valid = True
    for username in user_configs.keys():
        valid = test_user_config(username)
        all_valid = all_valid and valid
        print()  # Add spacing between users

    return all_valid


def main():
    """Main function to handle command line arguments."""
    parser = argparse.ArgumentParser(
        description="Manage Notion user configurations in .env file",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # List all configured users
  python scripts/manage_notion_users.py list

  # Add a new user
  python scripts/manage_notion_users.py add "John Doe" "secret_token_123" "page_id_456"

  # Update user's token
  python scripts/manage_notion_users.py update "John Doe" --token "new_token_123"

  # Update user's parent page ID
  python scripts/manage_notion_users.py update "John Doe" --parent-page-id "new_page_id_456"

  # Remove a user
  python scripts/manage_notion_users.py remove "John Doe"

  # Test all user configurations
  python scripts/manage_notion_users.py test

  # Test specific user configuration
  python scripts/manage_notion_users.py test "John Doe"
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # List command
    subparsers.add_parser("list", help="List all configured Notion users")

    # Add command
    add_parser = subparsers.add_parser("add", help="Add a new Notion user")
    add_parser.add_argument("username", help="Username (can contain spaces)")
    add_parser.add_argument("token", help="Notion integration token")
    add_parser.add_argument("parent_page_id", help="Parent page or database ID")

    # Update command
    update_parser = subparsers.add_parser("update", help="Update existing user configuration")
    update_parser.add_argument("username", help="Username to update")
    update_parser.add_argument("--token", help="New Notion integration token")
    update_parser.add_argument("--parent-page-id", help="New parent page or database ID")

    # Remove command
    remove_parser = subparsers.add_parser("remove", help="Remove a Notion user")
    remove_parser.add_argument("username", help="Username to remove")

    # Test command
    test_parser = subparsers.add_parser("test", help="Test user configurations")
    test_parser.add_argument("username", nargs="?", help="Username to test (optional, tests all if not provided)")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        if args.command == "list":
            list_users()
        elif args.command == "add":
            success = add_user(args.username, args.token, args.parent_page_id)
            return 0 if success else 1
        elif args.command == "update":
            if not args.token and not args.parent_page_id:
                print("❌ At least one of --token or --parent-page-id must be specified")
                return 1
            success = update_user(args.username, args.token, args.parent_page_id)
            return 0 if success else 1
        elif args.command == "remove":
            success = remove_user(args.username)
            return 0 if success else 1
        elif args.command == "test":
            print("🚀 Notion Cattackle Configuration Validator\n")
            if args.username:
                # Test specific user
                success = test_user_config(args.username)
            else:
                # Test all configurations
                success = test_all_configs()

            print("=" * 50)
            if success:
                print("🎉 All configuration tests passed!")
                print("✅ Notion cattackle is ready to use")
                return 0
            else:
                print("❌ Some configuration tests failed")
                print("Please fix the issues above before using the cattackle")
                return 1

        return 0

    except Exception as e:
        print(f"❌ Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
