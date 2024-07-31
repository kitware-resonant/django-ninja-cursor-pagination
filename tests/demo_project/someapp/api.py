from ninja import Router
from ninja.pagination import paginate
from pydantic import BaseModel

from ninja_cursor_pagination import CursorPagination

from .models import Category

router = Router()


class CategorySchema(BaseModel):
    title: str

    class Config:
        from_attributes = True


@router.get("/categories", response=list[CategorySchema])
@paginate(CursorPagination)
def list_categories(request):
    return Category.objects.order_by("title")
