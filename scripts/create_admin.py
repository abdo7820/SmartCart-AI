import argparse
import getpass
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from smartcart import accounts, appdb  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="Create (or promote) an administrator. The password is read from ADMIN_PASSWORD or prompted, never from arguments.")
    ap.add_argument("--email", default=os.environ.get("ADMIN_EMAIL"))
    ap.add_argument("--name", default=os.environ.get("ADMIN_NAME", "Administrator"))
    ap.add_argument("--promote", action="store_true", help="promote an existing user account to admin")
    a = ap.parse_args()
    if not a.email:
        sys.exit("give --email or set ADMIN_EMAIL")
    password = os.environ.get("ADMIN_PASSWORD")
    existing = None
    adb = appdb.open_app_db()
    appdb.migrate(adb)
    existing = accounts.get_account_by_email(adb, a.email)
    if existing is None or not a.promote:
        if existing is None and not password:
            password = getpass.getpass("Admin password: ")
            if password != getpass.getpass("Repeat password: "):
                sys.exit("passwords do not match")
    try:
        acc, how = accounts.provision_admin(adb, a.email, a.name, password or "", promote=a.promote)
    except ValueError as e:
        sys.exit(f"error: {e}")
    print(f"admin {how}: {acc['email']}")


if __name__ == "__main__":
    main()
