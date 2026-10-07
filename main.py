from fastapi import FastAPI

app = FastAPI(title="Course Catalog API")


@app.get("/")
def read_root():
    return {"message": "Course Catalog API is running"}
