from peewee import AutoField, CharField, DateTimeField, ForeignKeyField, TextField

from app.database import BaseModel
from app.models.url import Url
from app.models.user import User


class Event(BaseModel):
    id = AutoField()
    url = ForeignKeyField(Url, backref="events", column_name="url_id")
    user = ForeignKeyField(User, backref="events", column_name="user_id")
    event_type = CharField(max_length=50)
    timestamp = DateTimeField()
    details = TextField(null=True)  # stored as JSON string

    class Meta:
        table_name = "events"
