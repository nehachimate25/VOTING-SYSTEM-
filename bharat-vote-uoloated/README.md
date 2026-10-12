# 🇮🇳 Bharat Vote — Tkinter Edition

A secure Indian digital voting system built with **pure Python standard library** — no heavy frameworks needed.

---

## Libraries Used (all standard library)

| Library    | Role in this project |
|------------|----------------------|
| `tkinter`  | Full GUI — all windows, frames, buttons, dialogs |
| `sqlite3`  | Relational database for users & votes (`data/evoting.db`) |
| `pickle`   | Binary backup of every vote with Python `datetime` objects (`data/votes_backup.pkl`) |
| `hashlib`  | SHA-256 password hashing — passwords never stored in plain text |
| `datetime` | Timestamps on every vote, registration, and the pickle audit log |
| `csv`      | Admin export of voter data |

---

## Run

```bash
python main.py
```

> Requires Python 3.10+. No pip installs needed.

---

## Features

- **Splash screen** with animated progress bar
- **Register** — Full name, mobile, DOB (18+ check), Aadhaar (12-digit), password with strength meter
- **Login** — Aadhaar OR Voter ID + password (SHA-256 verified)
- **Vote** — 5 real Indian parties with colour-coded cards; one-vote-per-user enforced
- **Results** — Live visual bar charts, stat tiles, pickle audit log showing datetime of each vote
- **Admin** — Password-protected dashboard: view all users, search, delete, reset votes, export CSV
- **Auto logout** — 5-minute idle session timeout

---

## File Structure

```
bharat-vote-tkinter/
├── main.py        ← Entry point + all page classes
├── database.py    ← SQLite + Pickle + Hashlib + Datetime logic
├── theme.py       ← Dark navy tricolor color palette & fonts
├── widgets.py     ← Reusable Tkinter components (Toast, Card, etc.)
├── requirements.txt
└── data/          ← Created automatically on first run
    ├── evoting.db       (SQLite database)
    └── votes_backup.pkl (Pickle backup)
```

---

## Default Admin Credentials

```
Username: admin
Password: admin123
```

---

## How Pickle + Datetime works

Every time a vote is cast, a Python `datetime` object is stored inside the pickle file:

```python
data[voter_id] = {
    "party":    "BJP",
    "voted_at": datetime.now()   # real Python datetime object, not a string
}
pickle.dump(data, f)
```

The Results page reads this file and displays the datetime audit log.
