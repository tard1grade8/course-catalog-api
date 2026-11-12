from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from graphql_api import graphql_app

from db import get_db
import problem
from models import Course, Enrollment, Student
from schemas import (
    CourseOut,
    CourseStats,
    EnrollmentDetail,
    EnrollmentIn,
    EnrollmentOut,
    StudentIn,
    StudentOut,
)
import services
import counter

app = FastAPI(title="Course Catalog API")
problem.install(app)
counter.install(app)

app.include_router(graphql_app, prefix="/graphql")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SessionDep = Annotated[Session, Depends(get_db)]


def pagination(page: int = 1, page_size: int = 20):
    return {"offset": (page - 1) * page_size, "limit": page_size}


@app.get("/")
def read_root():
    return {"message": "Course Catalog API is running"}


@app.get("/courses", response_model=list[CourseOut])
def list_courses(
    db: SessionDep,
    is_elective: bool | None = None,
    level: str | None = None,
    sort: str = "popular",
    p: dict = Depends(pagination),
):
    stmt = select(Course)
    if is_elective is not None:
        stmt = stmt.where(Course.is_elective == is_elective)

    if level is not None:
        stmt = stmt.where(Course.level == level)

    if sort == "title":
        stmt = stmt.order_by(Course.title)
    else:
        stmt = stmt.order_by(Course.likes.desc(), Course.id)

    stmt = stmt.limit(p["limit"]).offset(p["offset"])
    return db.scalars(stmt).all()


@app.get("/courses/{course_id}", response_model=CourseOut)
def get_course(course_id: str, db: SessionDep):
    course = db.get(Course, course_id)
    if course is None:
        raise services.ServiceError("COURSE_NOT_FOUND", "Course not found")
    return course


@app.post("/courses/{course_id}/like", response_model=CourseOut)
def like_course(course_id: str, db: SessionDep):
    return services.like_course(db, course_id)


@app.get("/students", response_model=list[StudentOut])
def get_students(db: SessionDep):
    return db.scalars(select(Student)).all()


@app.post("/students", response_model=StudentOut, status_code=201)
def create_student(data: StudentIn, db: SessionDep):
    return services.create_student(db, name=data.name, email=data.email)


@app.post("/enrollments", response_model=EnrollmentOut, status_code=201)
def create_enrollment(data: EnrollmentIn, db: SessionDep):
    return services.enroll(db, course_id=data.course_id, student_id=data.student_id)

@app.get("/stats/courses", response_model=list[CourseStats])
def course_stats(db: SessionDep):
    enrolled = func.count(Enrollment.id).label("enrolled")
    stmt = (
        select(Course.id.label("course_id"), enrolled)
        .outerjoin(Course.enrollments)
        .group_by(Course.id)
        .order_by(enrolled.desc(), Course.id)
    )
    return db.execute(stmt).all()

def enrollment_details():
    return (
        select(
            Enrollment.id,
            Enrollment.course_id,
            Enrollment.student_id,
            Enrollment.enrolled_at,
            Course.title.label("course_title"),
            Student.name.label("student_name")
        )
        .join(Course)
        .join(Student)
        .order_by(Enrollment.id)
    )

@app.get("/enrollments", response_model=list[EnrollmentDetail])
def list_enrollments(db: SessionDep):
    return db.execute(enrollment_details()).all()

@app.get("/students/{student_id}", response_model=StudentOut)
def get_student(student_id: int, db: SessionDep):
    student = db.get(Student, student_id)
    if student is None:
        raise services.ServiceError("STUDENT_NOT_FOUND", "Student not found")
    return student

@app.get("/students/{student_id}/enrollments", response_model=list[EnrollmentDetail])
def list_student_enrollments(student_id: int, db: SessionDep):
    stmt = enrollment_details().where(Enrollment.student_id == student_id)
    return db.execute(stmt).all()