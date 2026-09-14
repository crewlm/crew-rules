from pydantic import BaseModel, Field, PrivateAttr, TypeAdapter


class CustomBaseModel(BaseModel):
    """
    Central base model for models to use to allow
    single place for defaults (like model strictness)
    etc.
    """

    pass
