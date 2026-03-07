from collections.abc import Sequence
from typing import Any, TypedDict, cast
from urllib import parse

from django.db.models import Model, QuerySet
from django.http import HttpRequest
from django.utils.translation import gettext as _
from ninja import Field, Schema
from ninja.pagination import PaginationBase
from pydantic import field_validator

from ._cursor import Cursor

MAX_PAGE_SIZE = 100


def _reverse_order(order: Sequence[str]) -> tuple[str, ...]:
    # Reverse the ordering specification for a Django ORM query.
    # Given an order_by tuple such as `('-created', 'uuid')` reverse the
    # ordering and return a new tuple, eg. `('created', '-uuid')`.
    def invert(x: str) -> str:
        return x[1:] if x.startswith("-") else f"-{x}"

    return tuple(invert(item) for item in order)


def _replace_query_param(url: str, key: str, val: str) -> str:
    scheme, netloc, path, query, fragment = parse.urlsplit(url)
    query_dict = parse.parse_qs(query, keep_blank_values=True)
    query_dict[key] = [val]
    query = parse.urlencode(sorted(query_dict.items()), doseq=True)
    return parse.urlunsplit((scheme, netloc, path, query, fragment))


class CursorPagination(PaginationBase):
    items_attribute = "results"
    default_ordering = ("-created",)

    class Input(Schema):
        limit: int = Field(
            MAX_PAGE_SIZE,
            ge=0,
            le=MAX_PAGE_SIZE,
            allow_inf_nan=False,
            description=_("Number of results to return per page."),
        )
        # This ought to be a Cursor type, but Ninja always tries to parse out the individual fields
        # of the Cursor from the query string before we get control. If Ninja didn't do this, we
        # could just use "WithJsonSchema" to fake the schema. So, tell Ninja that this is a string,
        # but use the validator and a "cast" to use it as a real Cursor. Trying to convert it to a
        # Cursor after validation causes errors to be raised too late.
        cursor: str = Field(
            "",
            description=_("The pagination cursor value."),
        )

        @field_validator("cursor", mode="after")
        @classmethod
        def _validate_cursor(cls, value: str) -> Cursor:
            return Cursor.model_validate(value)

    class Output(Schema):
        results: list[Any] = Field(description=_("The page of objects."))
        count: int = Field(
            description=_("The total number of results across all pages."),
        )
        next: str | None = Field(
            description=_("URL of next page of results if there is one."),
        )
        previous: str | None = Field(
            description=_("URL of previous page of results if there is one."),
        )

    def paginate_queryset(  # type: ignore[override]
        self,
        queryset: QuerySet,
        *,
        pagination: Input,
        request: HttpRequest,
        **params,
    ) -> dict[str, Any]:
        limit = pagination.limit
        cursor = cast("Cursor", pagination.cursor)

        if not queryset.query.order_by:
            queryset = queryset.order_by(*self.default_ordering)
        order = queryset.query.order_by

        if cursor.reverse:
            queryset = queryset.order_by(*_reverse_order(order))

        total_count = queryset.count()

        if cursor.position is not None:
            is_reversed = order[0].startswith("-")
            order_attr = order[0].lstrip("-")

            if cursor.reverse != is_reversed:
                queryset = queryset.filter(**{f"{order_attr}__lt": cursor.position})
            else:
                queryset = queryset.filter(**{f"{order_attr}__gt": cursor.position})

        # If we have an offset cursor then offset the entire page by that amount.
        # We also always fetch an extra item in order to determine if there is a
        # page following on from this one.
        results = list(queryset[cursor.offset : cursor.offset + limit + 1])
        page = list(results[:limit])

        # Determine the position of the final item following the page.
        if len(results) > len(page):
            has_following_position = True
            following_position = self._get_position_from_instance(results[-1], order)
        else:
            has_following_position = False
            following_position = None

        if cursor.reverse:
            # If we have a reverse queryset, then the query ordering was in reverse
            # so we need to reverse the items again before returning them to the user.
            page.reverse()

            has_next = (cursor.position is not None) or (cursor.offset > 0)
            has_previous = has_following_position
            next_position = cursor.position if has_next else None
            previous_position = following_position if has_previous else None
        else:
            has_next = has_following_position
            has_previous = (cursor.position is not None) or (cursor.offset > 0)
            next_position = following_position if has_next else None
            previous_position = cursor.position if has_previous else None

        base_url = request.build_absolute_uri()
        return {
            "results": page,
            "count": total_count,
            "next": self.next_link(
                base_url=base_url,
                page=page,
                cursor=cursor,
                order=order,
                has_previous=has_previous,
                limit=limit,
                next_position=next_position,
                previous_position=previous_position,
            )
            if has_next
            else None,
            "previous": self.previous_link(
                base_url=base_url,
                page=page,
                cursor=cursor,
                order=order,
                has_next=has_next,
                limit=limit,
                next_position=next_position,
                previous_position=previous_position,
            )
            if has_previous
            else None,
        }

    def _encode_cursor(self, cursor: Cursor, base_url: str) -> str:
        encoded = cursor.model_dump(exclude_defaults=True)
        return _replace_query_param(base_url, "cursor", encoded)

    def next_link(  # noqa: PLR0913
        self,
        *,
        base_url: str,
        page: list,
        cursor: Cursor,
        order: Sequence[str],
        has_previous: bool,
        limit: int,
        next_position: str | None,
        previous_position: str | None,
    ) -> str:
        compare = (
            self._get_position_from_instance(page[-1], order)
            # If we're reversing direction and we have an offset cursor
            # then we cannot use the first position we find as a marker.
            if page and cursor.reverse and cursor.offset
            else next_position
        )
        offset = 0

        position: str | None
        has_item_with_unique_position = False
        for item in reversed(page):
            position = self._get_position_from_instance(item, order)
            if position != compare:
                # The item in this position and the item following it
                # have different positions. We can use this position as
                # our marker.
                has_item_with_unique_position = True
                break

            # The item in this position has the same position as the item
            # following it, we can't use it as a marker position, so increment
            # the offset and keep seeking to the previous item.
            compare = position
            offset += 1  # noqa: SIM113

        if page and not has_item_with_unique_position:
            # There were no unique positions in the page.
            if not has_previous:
                # We are on the first page.
                # Our cursor will have an offset equal to the page size,
                # but no position to filter against yet.
                offset = limit
                position = None
            elif cursor.reverse:
                # The change in direction will introduce a paging artifact,
                # where we end up skipping forward a few extra items.
                offset = 0
                position = previous_position
            else:
                # Use the position from the existing cursor and increment
                # it's offset by the page size.
                offset = cursor.offset + limit
                position = previous_position

        if not page:
            position = next_position

        next_cursor = Cursor(offset=offset, reverse=False, position=position)
        return self._encode_cursor(next_cursor, base_url)

    def previous_link(  # noqa: PLR0913
        self,
        *,
        base_url: str,
        page: list,
        cursor: Cursor,
        order: Sequence[str],
        has_next: bool,
        limit: int,
        next_position: str | None,
        previous_position: str | None,
    ):
        compare = (
            self._get_position_from_instance(page[0], order)
            # If we're reversing direction and we have an offset cursor
            # then we cannot use the first position we find as a marker.
            if page and not cursor.reverse and cursor.offset
            else previous_position
        )
        offset = 0

        position: str | None
        has_item_with_unique_position = False
        for item in page:
            position = self._get_position_from_instance(item, order)
            if position != compare:
                # The item in this position and the item following it
                # have different positions. We can use this position as
                # our marker.
                has_item_with_unique_position = True
                break

            # The item in this position has the same position as the item
            # following it, we can't use it as a marker position, so increment
            # the offset and keep seeking to the previous item.
            compare = position
            offset += 1  # noqa: SIM113

        if page and not has_item_with_unique_position:
            # There were no unique positions in the page.
            if not has_next:
                # We are on the final page.
                # Our cursor will have an offset equal to the page size,
                # but no position to filter against yet.
                offset = limit
                position = None
            elif cursor.reverse:
                # Use the position from the existing cursor and increment
                # it's offset by the page size.
                offset = cursor.offset + limit
                position = next_position
            else:
                # The change in direction will introduce a paging artifact,
                # where we end up skipping back a few extra items.
                offset = 0
                position = next_position

        if not page:
            position = previous_position

        cursor = Cursor(offset=offset, reverse=True, position=position)
        return self._encode_cursor(cursor, base_url)

    def _get_position_from_instance(self, instance, ordering: Sequence[str]) -> str:
        field_name = ordering[0].lstrip("-")
        attr = instance[field_name] if isinstance(instance, dict) else getattr(instance, field_name)
        return str(attr)
