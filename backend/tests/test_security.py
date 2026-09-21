import re
from pathlib import Path

from app.core.security import verify_password


def test_sql_seed_passwords_match_documented_local_credentials():
    seed_sql = (Path(__file__).parents[2] / "database" / "seed.sql").read_text(encoding="utf-8")
    credentials = {
        "student01": "Student123!",
        "student02": "Student123!",
        "leader01": "Leader123!",
        "leader02": "Leader123!",
        "manager01": "Manager123!",
        "admin01": "Admin123!",
    }
    for username, password in credentials.items():
        match = re.search(rf"\(\d+, '{username}', '([^']+)'", seed_sql)
        assert match is not None
        assert verify_password(password, match.group(1))
