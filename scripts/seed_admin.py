from sqlmodel import Session, select
from app.db import engine, init_db
from app.models import User
from app.security import hash_password
import uuid

init_db()

ADMIN_EMAIL = "admin@example.com"
ADMIN_PASS = "admin"

with Session(engine) as s:
    user = s.exec(select(User).where(User.email==ADMIN_EMAIL)).first()
    if not user:
        u = User(
            id=str(uuid.uuid4()),
            first_name="Admin",
            last_name="User",
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASS),
            role="admin"
        )
        s.add(u); s.commit()
        print("Created admin:", ADMIN_EMAIL, ADMIN_PASS)
    else:
        print("Admin exists")
