# django-ninja-cursor-pagination

A [Django Ninja]((https://django-ninja.dev/)) extension for cursor-based pagination.

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

### `only_count_initial_page`

To improve performance on larger queries, the `only_count_initial_page` option can be used:
```python
@paginate(CursorPagination, only_count_initial_page=True)
```

This will cause `count` to be only be returned on the initial response and not on subsequent pages.
