from django.db.models import QuerySet
from django.http import HttpRequest
from ninja import Router
from ninja.pagination import paginate
from pydantic import BaseModel, ConfigDict

from ninja_cursor_pagination import CursorPagination

from .models import Category

router = Router()


class CategorySchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    title: str


@router.get("/categories", response=list[CategorySchema])
@paginate(CursorPagination)
def list_categories(request: HttpRequest) -> QuerySet[Category]:
    return Category.objects.order_by("title")
