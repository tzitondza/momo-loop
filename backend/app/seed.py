"""Seed demo users for the hackathon PoC."""

from __future__ import annotations

from sqlalchemy.orm import Session

from .auth import hash_password
from .database import SessionLocal, init_db
from .models import User

DEMO_USERS = [
    {
        "email": "viewer@mtn.demo",
        "full_name": "Thandi Viewer",
        "password": "viewer123",
        "role": "viewer",
        "region": "Gauteng",
    },
    {
        "email": "analyst@mtn.demo",
        "full_name": "Sipho Analyst",
        "password": "analyst123",
        "role": "analyst",
        "region": "Western Cape",
    },
    {
        "email": "lead@mtn.demo",
        "full_name": "Lindiwe Acquisition Lead",
        "password": "lead123",
        "role": "acquisition_lead",
        "region": "South Africa",
    },
    {
        "email": "admin@mtn.demo",
        "full_name": "MoMo Loop Admin",
        "password": "admin123",
        "role": "admin",
        "region": "South Africa",
    },
]


def seed_users(db: Session | None = None) -> list[str]:
    close = False
    if db is None:
        init_db()
        db = SessionLocal()
        close = True

    touched = []
    try:
        for item in DEMO_USERS:
            existing = db.query(User).filter(User.email == item["email"]).first()
            if existing:
                existing.full_name = item["full_name"]
                existing.role = item["role"]
                existing.region = item["region"]
                existing.is_active = True
                touched.append(f"updated:{item['email']}")
                continue
            user = User(
                email=item["email"],
                full_name=item["full_name"],
                hashed_password=hash_password(item["password"]),
                role=item["role"],
                region=item["region"],
            )
            db.add(user)
            touched.append(f"created:{item['email']}")
        db.commit()
    finally:
        if close:
            db.close()
    return touched


if __name__ == "__main__":
    init_db()
    made = seed_users()
    print(f"Database ready. Users: {made or 'none'}")
    print("Demo logins:")
    for u in DEMO_USERS:
        print(f"  {u['email']} / {u['password']}  [{u['role']}] region={u['region']}")
