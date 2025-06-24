from base64 import urlsafe_b64decode
import binascii

from hypothesis import given
from hypothesis import strategies as st
import pydantic
import pytest

from ninja_cursor_pagination._cursor import MAX_OFFSET, Cursor


@given(
    st.one_of(
        st.integers(max_value=-1),
        st.integers(min_value=101),
    ),
)
def test_cursor_offset_invalid(offset):
    with pytest.raises(pydantic.ValidationError, match=r"offset"):
        Cursor.model_validate({"offset": offset})


def test_cursor_serialize_empty():
    assert Cursor.model_validate({}).model_dump(exclude_defaults=True) == ""


@given(
    st.builds(
        Cursor,
        offset=st.integers(min_value=0, max_value=MAX_OFFSET),
        reverse=st.booleans(),
        position=st.one_of(st.text(), st.none()),
    ),
)
def test_cursor_serialize_valid(cursor):
    cursor.model_dump(exclude_defaults=True)


@given(
    st.builds(
        Cursor,
        offset=st.integers(min_value=0, max_value=MAX_OFFSET),
        reverse=st.booleans(),
        position=st.one_of(st.text(), st.none()),
    ),
)
def test_cursor_deserialize_valid(cursor):
    encoded_cursor = cursor.model_dump(exclude_defaults=True)
    decoded_cursor = Cursor.model_validate(encoded_cursor)

    assert decoded_cursor == cursor


def test_cursor_deserialize_empty():
    Cursor.model_validate("")


def _is_empty_base64(text: str) -> bool:
    try:
        return urlsafe_b64decode(text.encode()) == b""
    except (binascii.Error, UnicodeError):
        return False


@given(
    st.one_of(
        # Ensure that essentially empty Base64 with extra padding is rejected
        st.text(min_size=1).filter(_is_empty_base64),
        # It's theoretically possible for this to be valid input, but practically extremely unlikely
        st.text(min_size=1),
    ),
)
def test_cursor_deserialize_invalid(encoded_cursor):
    with pytest.raises(pydantic.ValidationError, match=r"cursor"):
        Cursor.model_validate(encoded_cursor)
