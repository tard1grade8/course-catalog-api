from sqlalchemy.orm import Session

from db import engine
from models import Course

with Session(engine) as alice, Session(engine) as bob:
    a = alice.get(Course, "api-design")
    b = bob.get(Course, "api-design")
    print(f"Alice reads {a.likes} | Bob reads {b.likes}")

    a.likes = Course.likes + 1
    alice.commit()

    b.likes = Course.likes + 1
    bob.commit()

with Session(engine) as session:
    print(f"in the database: {session.get(Course, 'api-design').likes}")