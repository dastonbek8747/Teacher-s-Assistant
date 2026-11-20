from pydantic import BaseModel, Field, EmailStr, field_validator


class CreateUSer(BaseModel):
    username: str
    email: EmailStr
    password: str
    confirm_password: str

    @field_validator("password")
    @classmethod
    def check_password(cls, _, values):
        if values.get("password") != values.get("confirm_password"):
            raise ValueError("Passwords don't match")
        raise values


class LoginUser(BaseModel):
    username: str
    password: str
