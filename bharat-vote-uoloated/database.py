"""
database.py — Bharat Vote (Tkinter Edition)
============================================
Libraries used:
  - sqlite3   : relational database for users & votes
  - pickle    : binary backup of vote records
  - hashlib   : SHA-256 password hashing
  - datetime  : timestamps for votes and registrations
"""

import sqlite3
import hashlib
import pickle
import random
import string
from datetime import datetime
from pathlib import Path

# ── Paths ────────────────────────────────────────────────────────────────────
DATA_DIR    = Path(__file__).parent / "data"
DATA_DIR.mkdir(exist_ok=True)
DB_PATH     = DATA_DIR / "evoting.db"
PICKLE_PATH = DATA_DIR / "votes_backup.pkl"

# ── Parties ──────────────────────────────────────────────────────────────────
PARTIES = [
    {"name": "BJP",       "full": "Bharatiya Janata Party",     "emoji": "🌸", "color": "#FF6B00"},
    {"name": "INC",       "full": "Indian National Congress",   "emoji": "✋", "color": "#19AAED"},
    {"name": "AAP",       "full": "Aam Aadmi Party",            "emoji": "🧹", "color": "#4F9AE8"},
    {"name": "Shiv Sena", "full": "Shiv Sena",                  "emoji": "🏹", "color": "#F79321"},
    {"name": "NCP",       "full": "Nationalist Congress Party", "emoji": "⏰", "color": "#00B5E2"},
]
PARTY_NAMES = [p["name"] for p in PARTIES]

ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

# ── Helpers ───────────────────────────────────────────────────────────────────
def hash_password(password: str) -> str:
    """SHA-256 hash — passwords are NEVER stored in plain text."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def generate_voter_id() -> str:
    chars = string.ascii_uppercase + string.digits
    return "VOT-" + "".join(random.choices(chars, k=8))


def calculate_age(dob_str: str) -> int:
    """dob_str format: DD/MM/YYYY"""
    dob = datetime.strptime(dob_str, "%d/%m/%Y")
    today = datetime.today()
    return today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))


def now_iso() -> str:
    return datetime.now().isoformat(sep=" ", timespec="seconds")


def fmt_dt(iso: str) -> str:
    """Pretty-print a stored ISO timestamp."""
    try:
        dt = datetime.fromisoformat(iso)
        return dt.strftime("%d %b %Y  %I:%M %p")
    except Exception:
        return iso or "—"


# ── Schema ────────────────────────────────────────────────────────────────────
def _conn():
    return sqlite3.connect(DB_PATH)


def init_db():
    con = _conn()
    cur = con.cursor()
    cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            full_name     TEXT NOT NULL,
            mobile        TEXT NOT NULL,
            dob           TEXT NOT NULL,
            aadhar        TEXT UNIQUE NOT NULL,
            voter_id      TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            has_voted     INTEGER DEFAULT 0,
            voted_party   TEXT,
            voted_at      TEXT,
            created_at    TEXT NOT NULL,
            location      TEXT DEFAULT 'Other'
        );
        CREATE TABLE IF NOT EXISTS votes (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            voter_id  TEXT NOT NULL,
            party     TEXT NOT NULL,
            voted_at  TEXT NOT NULL
        );
    """)
    con.commit()
    # Add location column if it doesn't exist (for existing databases)
    try:
        con.execute("ALTER TABLE users ADD COLUMN location TEXT DEFAULT 'Other'")
        con.commit()
    except sqlite3.OperationalError:
        pass  # column already exists
    con.close()
    # Initialise pickle backup if missing
    if not PICKLE_PATH.exists():
        _pickle_save({})


# ── Pickle helpers ─────────────────────────────────────────────────────────────
def _pickle_load() -> dict:
    try:
        with open(PICKLE_PATH, "rb") as f:
            return pickle.load(f)
    except Exception:
        return {}


def _pickle_save(data: dict):
    with open(PICKLE_PATH, "wb") as f:
        pickle.dump(data, f)


# ── User CRUD ─────────────────────────────────────────────────────────────────
def register_user(full_name, mobile, dob, aadhar, password, location="Other"):
    """Returns (success: bool, message: str, voter_id: str | None)."""
    try:
        age = calculate_age(dob)
    except ValueError:
        return False, "Date of Birth must be in DD/MM/YYYY format (e.g. 15/08/1995).", None
    if age < 18:
        return False, "You must be at least 18 years old to register.", None
    if len(aadhar) != 12 or not aadhar.isdigit():
        return False, "Aadhaar must be exactly 12 digits.", None
    if len(mobile) != 10 or not mobile.isdigit():
        return False, "Mobile number must be exactly 10 digits.", None
    if len(password) < 6:
        return False, "Password must be at least 6 characters.", None

    voter_id = generate_voter_id()
    try:
        con = _conn()
        con.execute("""
            INSERT INTO users
              (full_name, mobile, dob, aadhar, voter_id, password_hash, created_at, location)
            VALUES (?,?,?,?,?,?,?,?)
        """, (full_name, mobile, dob, aadhar, voter_id,
              hash_password(password), now_iso(), location))
        con.commit()
        con.close()
        return True, "Registration successful!", voter_id
    except sqlite3.IntegrityError:
        return False, "Aadhaar is already registered.", None


def login_user(identifier: str, password: str):
    """identifier = Aadhaar OR Voter ID. Returns user dict or None."""
    con = _conn()
    con.row_factory = sqlite3.Row
    row = con.execute("""
        SELECT * FROM users
        WHERE (aadhar = ? OR voter_id = ?) AND password_hash = ?
    """, (identifier, identifier, hash_password(password))).fetchone()
    con.close()
    return dict(row) if row else None


def get_user_by_voter_id(voter_id: str):
    con = _conn()
    con.row_factory = sqlite3.Row
    row = con.execute("SELECT * FROM users WHERE voter_id=?", (voter_id,)).fetchone()
    con.close()
    return dict(row) if row else None


def get_all_users():
    con = _conn()
    con.row_factory = sqlite3.Row
    rows = con.execute("SELECT * FROM users ORDER BY id DESC").fetchall()
    con.close()
    return [dict(r) for r in rows]


def delete_user(voter_id: str):
    con = _conn()
    con.execute("DELETE FROM users WHERE voter_id=?", (voter_id,))
    con.commit()
    con.close()


# ── Voting ────────────────────────────────────────────────────────────────────
def cast_vote(voter_id: str, party: str):
    """Returns (success: bool, message: str)."""
    user = get_user_by_voter_id(voter_id)
    if not user:
        return False, "User not found."
    if user["has_voted"]:
        return False, "You have already voted."

    ts = now_iso()
    con = _conn()
    con.execute("UPDATE users SET has_voted=1, voted_party=?, voted_at=? WHERE voter_id=?",
                (party, ts, voter_id))
    con.execute("INSERT INTO votes (voter_id, party, voted_at) VALUES (?,?,?)",
                (voter_id, party, ts))
    con.commit()
    con.close()

    # Pickle backup with datetime timestamp
    data = _pickle_load()
    data[voter_id] = {"party": party, "voted_at": datetime.now()}   # store actual datetime obj
    _pickle_save(data)

    return True, "Vote cast successfully!"


def get_results() -> dict:
    """Returns {party_name: count}."""
    con = _conn()
    rows = con.execute(
        "SELECT party, COUNT(*) FROM votes GROUP BY party"
    ).fetchall()
    con.close()
    results = {row[0]: row[1] for row in rows}
    for p in PARTY_NAMES:
        results.setdefault(p, 0)
    return results


def get_location_results() -> dict:
    """Returns {location: {party_name: count}} for all locations that have votes."""
    con = _conn()
    rows = con.execute("""
        SELECT u.location, v.party, COUNT(*) as cnt
        FROM votes v
        JOIN users u ON u.voter_id = v.voter_id
        GROUP BY u.location, v.party
    """).fetchall()
    locations_row = con.execute(
        "SELECT DISTINCT location FROM users WHERE location IS NOT NULL"
    ).fetchall()
    con.close()

    loc_results = {}
    for loc_row in locations_row:
        loc = loc_row[0] or "Other"
        loc_results[loc] = {p: 0 for p in PARTY_NAMES}
    for location, party, cnt in rows:
        loc = location or "Other"
        if loc not in loc_results:
            loc_results[loc] = {p: 0 for p in PARTY_NAMES}
        loc_results[loc][party] = cnt
    return loc_results


def get_stats() -> dict:
    con = _conn()
    total_users = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    total_votes = con.execute("SELECT COUNT(*) FROM votes").fetchone()[0]
    con.close()
    results = get_results()
    top_party = max(results, key=results.get) if total_votes else "—"
    turnout = f"{total_votes/total_users*100:.1f}%" if total_users else "0%"
    return {
        "total_users": total_users,
        "total_votes": total_votes,
        "top_party":   top_party,
        "turnout":     turnout,
        "results":     results,
        "location_results": get_location_results(),
    }


def get_pickle_log() -> list[dict]:
    """Return pickle backup as a sorted list of dicts."""
    data = _pickle_load()
    rows = []
    for vid, info in data.items():
        dt = info.get("voted_at")
        rows.append({
            "voter_id": vid,
            "party":    info.get("party", "?"),
            "voted_at": dt.strftime("%d %b %Y  %I:%M:%S %p") if isinstance(dt, datetime) else str(dt),
        })
    rows.sort(key=lambda r: r["voted_at"])
    return rows


def reset_all_votes():
    con = _conn()
    con.execute("DELETE FROM votes")
    con.execute("UPDATE users SET has_voted=0, voted_party=NULL, voted_at=NULL")
    con.commit()
    con.close()
    _pickle_save({})


def export_csv(path: str):
    import csv
    users = get_all_users()
    fields = ["full_name", "mobile", "dob", "aadhar", "voter_id",
              "has_voted", "voted_party", "voted_at", "created_at"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(users)
    return path


def password_strength(pw: str) -> int:
    score = 0
    if len(pw) >= 8:                                        score += 25
    if any(c.isupper() for c in pw):                       score += 20
    if any(c.isdigit() for c in pw):                       score += 20
    if any(c in "!@#$%^&*()_+-=[]{}|;:,.<>?" for c in pw): score += 20
    if len(pw) >= 12:                                       score += 15
    return min(score, 100)
