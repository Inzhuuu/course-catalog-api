from datetime import datetime
from typing import Annotated

import strawberry
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from strawberry.fastapi import BaseContext, GraphQLRouter
from strawberry.types import Info

import services
from db import get_db
from models import Course, Enrollment, Student


class Context(BaseContext):
    def __init__(self, db: Session):
        super().__init__()
        self.db = db


def get_context(db: Annotated[Session, Depends(get_db)]) -> Context:
    return Context(db)


@strawberry.type(name="Course")
class CourseType:
    id: strawberry.ID
    title: str
    description: str
    credits: int
    is_elective: bool
    likes: int
    level: str
    enrollments: list["EnrollmentType"]


@strawberry.type(name="Student")
class StudentType:
    id: strawberry.ID
    name: str
    email: str
    enrollments: list["EnrollmentType"]


@strawberry.type(name="Enrollment")
class EnrollmentType:
    id: strawberry.ID
    enrolled_at: datetime
    course: CourseType
    student: StudentType


@strawberry.type
class Query:
    @strawberry.field
    def courses(
        self, info: Info, is_elective: bool | None = None, limit: int = 20
    ) -> list[CourseType]:
        stmt = select(Course).order_by(Course.likes.desc(), Course.id).limit(limit)
        if is_elective is not None:
            stmt = stmt.where(Course.is_elective == is_elective)
        return info.context.db.scalars(stmt).all()

    @strawberry.field
    def course(self, info: Info, id: strawberry.ID) -> CourseType | None:
        return info.context.db.get(Course, id)

    @strawberry.field
    def students(self, info: Info, limit: int = 20) -> list[StudentType]:
        stmt = select(Student).order_by(Student.id).limit(limit)
        return info.context.db.scalars(stmt).all()

    @strawberry.field
    def student(self, info: Info, id: strawberry.ID) -> StudentType | None:
        return info.context.db.get(Student, int(id))

    @strawberry.field
    def enrollments(self, info: Info, limit: int = 20) -> list[EnrollmentType]:
        stmt = select(Enrollment).order_by(Enrollment.id).limit(limit)
        return info.context.db.scalars(stmt).all()


@strawberry.type
class UserError:
    code: str
    message: str


@strawberry.input
class EnrollInput:
    course_id: strawberry.ID
    student_id: strawberry.ID


@strawberry.type
class EnrollPayload:
    enrollment: EnrollmentType | None = None
    user_errors: list[UserError] = strawberry.field(default_factory=list)


@strawberry.type
class LikePayload:
    course: CourseType | None = None
    user_errors: list[UserError] = strawberry.field(default_factory=list)


def as_user_errors(err: services.ServiceError) -> list[UserError]:
    return [UserError(code=err.code, message=err.message)]


@strawberry.type
class Mutation:
    @strawberry.mutation
    def enroll(self, info: Info, input: EnrollInput) -> EnrollPayload:
        try:
            enrollment = services.enroll(
                info.context.db, input.course_id, int(input.student_id)
            )
        except services.ServiceError as err:
            return EnrollPayload(user_errors=as_user_errors(err))
        return EnrollPayload(enrollment=enrollment)

    @strawberry.mutation
    def like_course(self, info: Info, id: strawberry.ID) -> LikePayload:
        try:
            course = services.like_course(info.context.db, id)
        except services.ServiceError as err:
            return LikePayload(user_errors=as_user_errors(err))
        return LikePayload(course=course)


schema = strawberry.Schema(query=Query, mutation=Mutation)
graphql_app = GraphQLRouter(schema, context_getter=get_context)
