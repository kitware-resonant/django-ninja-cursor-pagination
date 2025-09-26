from __future__ import annotations

from base64 import urlsafe_b64decode, urlsafe_b64encode
import binascii
from collections.abc import Callable
from typing import TYPE_CHECKING, Annotated, Any, Literal
from urllib.parse import parse_qsl, urlencode

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PlainSerializer,
    model_serializer,
    model_validator,
)
from pydantic.main import IncEx
from pydantic_core.core_schema import SerializerFunctionWrapHandler

# Limit to protect against possibly malicious queries
MAX_OFFSET = 100

CompactBool = Annotated[bool, PlainSerializer(lambda value: "1" if value else "0", return_type=str)]


class Cursor(BaseModel):
    offset: int = Field(0, ge=0, le=MAX_OFFSET, allow_inf_nan=False, alias="o")
    reverse: CompactBool = Field(False, alias="r")
    position: str | None = Field(None, alias="p")

    model_config = ConfigDict(
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )

    @model_validator(mode="before")
    @classmethod
    def _deserialize_base64(cls, data: Any) -> Any:
        if isinstance(data, str):
            try:
                if not data:
                    # An actually empty input is just a compact representation of all default values
                    return {}
                url_string = urlsafe_b64decode(data).decode()
                # "strict_parsing" will reject empty values
                return dict(parse_qsl(url_string, keep_blank_values=True, strict_parsing=True))
            except (binascii.Error, UnicodeError, ValueError) as error:
                raise ValueError(f"Invalid {cls.__name__.lower()}") from error
        return data

    @model_serializer(mode="wrap")
    def _serialize_base64(self, serialize: SerializerFunctionWrapHandler) -> str:
        dict_data = serialize(self)
        url_string = urlencode(dict_data)
        return urlsafe_b64encode(url_string.encode()).decode()

    if TYPE_CHECKING:
        # Ensure type checkers see the correct return type
        def model_dump(  # type: ignore[override]
            self,
            *,
            mode: Literal["json", "python"] | str = "python",
            include: IncEx | None = None,
            exclude: IncEx | None = None,
            context: Any | None = None,
            by_alias: bool | None = None,
            exclude_unset: bool = False,
            exclude_defaults: bool = False,
            exclude_none: bool = False,
            round_trip: bool = False,
            warnings: bool | Literal["none", "warn", "error"] = True,
            fallback: Callable[[Any], Any] | None = None,
            serialize_as_any: bool = False,
        ) -> str: ...
