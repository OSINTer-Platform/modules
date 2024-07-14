from typing import Self

from pydantic import (
    BaseModel,
    ValidationInfo,
    model_validator,
)
from pydantic_core import PydanticCustomError


class AbstractDocument(BaseModel):
    id: str


class AbstractPartialDocument(BaseModel):
    id: str

    @model_validator(mode="after")
    def check_required_values(self, info: ValidationInfo) -> Self:
        context = info.context

        if not context:
            raise PydanticCustomError(
                "missing_validation_context",
                "No context was provided for validating partial document",
            )

        try:
            fields_to_validate: None | list["str"] = context.get(
                "fields_to_validate", None
            )
        except AttributeError:
            raise PydanticCustomError(
                "invalid_field_to_validate",
                "The value passed to the field-to-validate context variable should be a dictionary",
            )

        if not fields_to_validate or len(fields_to_validate) < 1:
            raise PydanticCustomError(
                "missing_fields_to_validate",
                "No list of fields to validate was provided",
            )

        for field_name in fields_to_validate:
            if getattr(self, field_name, None) is None:
                raise ValueError(f"Missing value for {field_name}")

        return self
