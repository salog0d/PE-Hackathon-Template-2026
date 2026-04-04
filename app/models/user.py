from peewee import AutoField, CharField, DateTimeField

from app.database import BaseModel


class User(BaseModel):
    id = AutoField()
    username = CharField(max_length=255, unique=True)
    email = CharField(max_length=255, unique=True)
    created_at = DateTimeField()

    class Meta:
        table_name = "users"
