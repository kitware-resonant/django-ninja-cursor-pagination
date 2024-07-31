# django-ninja-cursor-pagination

This library adds a new pagination class for use with [django-ninja](https://django-ninja.dev/)
which supports cursor-based pagination.

## Installation

`pip install django-ninja-cursor-pagination`

## Usage

```python
from ninja.pagination import paginate
from ninja_cursor_pagination import CursorPagination

@router.get("/things", response=list[ThingSchema])
@paginate(CursorPagination)
def list_things(request):
    return Thing.objects.order_by("title")
```
