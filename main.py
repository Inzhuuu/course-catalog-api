from fastapi import FastAPI

from data import find_course, get_all_courses
from models import Course

app = FastAPI(title="Course Catalog API")


@app.get("/")
def read_root():
    return {"message": "Course Catalog API is running"}


@app.get("/courses", response_model=list[Course])
def list_courses():
    return get_all_courses()
