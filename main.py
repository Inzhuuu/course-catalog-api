from fastapi import Depends, FastAPI, HTTPException

from data import find_course, get_all_courses
from models import Course

app = FastAPI(title="Course Catalog API")


def pagination(page: int = 1, page_size: int = 20):
    return {"offset": (page - 1) * page_size, "limit": page_size}


@app.get("/")
def read_root():
    return {"message": "Course Catalog API is running"}


@app.get("/courses", response_model=list[Course])
def list_courses(
    is_elective: bool | None = None,
    sort: str = "popular",
    p: dict = Depends(pagination),
):
    courses = get_all_courses()
    if is_elective is not None:
        courses = [c for c in courses if c.is_elective == is_elective]
    if sort == "title":
        courses = sorted(courses, key=lambda c: c.title)
    else:
        courses = sorted(courses, key=lambda c: c.likes, reverse=True)
    offset, limit = p["offset"], p["limit"]
    return courses[offset : offset + limit]


@app.get("/courses/{course_id}", response_model=Course)
def get_course(course_id: str):
    course = find_course(course_id)
    if course is None:
        raise HTTPException(status_code=404, detail="Course not found")
    return course
