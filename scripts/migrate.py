import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from smartcart import appdb  # noqa: E402

adb = appdb.open_app_db()
applied = appdb.migrate(adb)
print("applied:", applied or "nothing to apply")
