from fastapi import FastAPI, HTTPException

from data import find_course, get_all_courses
from models import Course

app = FastAPI(title="Course Catalog API")


@app.get("/")
def read_root():
    return {"message": "Course Catalog API is running"}


@app.get("/courses", response_model=list[Course])
def list_courses(is_elective: bool | None = None, sort: str = "popular"):
    courses = get_all_courses()
    if is_elective is not None:
        courses = [c for c in courses if c.is_elective == is_elective]
    if sort == "title":
        courses = sorted(courses, key=lambda c: c.title)
    else:
        courses = sorted(courses, key=lambda c: c.likes, reverse=True)
    return courses


@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str):
    course = find_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
