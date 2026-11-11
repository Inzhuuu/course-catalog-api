from typing import Annotated

import strawberry
from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.orm import Session
from strawberry.fastapi import BaseContext, GraphQLRouter
from strawberry.types import Info

from db import get_db
from models import Course


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


schema = strawberry.Schema(query=Query)
graphql_app = GraphQLRouter(schema, context_getter=get_context)
