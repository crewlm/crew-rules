from pydantic import BaseModel, Field, PrivateAttr, GetCoreSchemaHandler
from pydantic_core import core_schema


class CustomBaseModel(BaseModel):
    """
    Central base model for models to use to allow
    single place for defaults (like model strictness)
    etc.
    """

    pass
