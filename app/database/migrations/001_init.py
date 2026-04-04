"""Peewee migrations -- 001_init.py.

Some examples (model - class or model name)::

    > Model = migrator.orm['table_name']            # Return model in current state by name
    > Model = migrator.ModelClass                   # Return model in current state by name

    > migrator.sql(sql)                             # Run custom SQL
    > migrator.run(func, *args, **kwargs)           # Run python function with the given args
    > migrator.create_model(Model)                  # Create a model (could be used as decorator)
    > migrator.remove_model(model, cascade=True)    # Remove a model
    > migrator.add_fields(model, **fields)          # Add fields to a model
    > migrator.change_fields(model, **fields)       # Change fields
    > migrator.remove_fields(model, *field_names, cascade=True)
    > migrator.rename_field(model, old_field_name, new_field_name)
    > migrator.rename_table(model, new_table_name)
    > migrator.add_index(model, *col_names, unique=False)
    > migrator.add_not_null(model, *field_names)
    > migrator.add_default(model, field_name, default)
    > migrator.add_constraint(model, name, sql)
    > migrator.drop_index(model, *col_names)
    > migrator.drop_not_null(model, *field_names)
    > migrator.drop_constraints(model, *constraints)

"""

from contextlib import suppress

import peewee as pw
from peewee_migrate import Migrator


with suppress(ImportError):
    import playhouse.postgres_ext as pw_pext


def migrate(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your migrations here."""
    
    @migrator.create_model
    class BaseModel(pw.Model):
        id = pw.AutoField()

        class Meta:
            table_name = "basemodel"

    @migrator.create_model
    class User(pw.Model):
        id = pw.AutoField()
        username = pw.CharField(max_length=255, unique=True)
        email = pw.CharField(max_length=255, unique=True)
        created_at = pw.DateTimeField()

        class Meta:
            table_name = "users"

    @migrator.create_model
    class Url(pw.Model):
        id = pw.AutoField()
        user = pw.ForeignKeyField(column_name='user_id', field='id', model=migrator.orm['users'])
        short_code = pw.CharField(max_length=20, unique=True)
        original_url = pw.CharField(max_length=2048)
        title = pw.CharField(max_length=255, null=True)
        is_active = pw.BooleanField(default=True)
        created_at = pw.DateTimeField()
        updated_at = pw.DateTimeField()

        class Meta:
            table_name = "urls"

    @migrator.create_model
    class Event(pw.Model):
        id = pw.AutoField()
        url = pw.ForeignKeyField(column_name='url_id', field='id', model=migrator.orm['urls'])
        user = pw.ForeignKeyField(column_name='user_id', field='id', model=migrator.orm['users'])
        event_type = pw.CharField(max_length=50)
        timestamp = pw.DateTimeField()
        details = pw.TextField(null=True)

        class Meta:
            table_name = "events"


def rollback(migrator: Migrator, database: pw.Database, *, fake=False):
    """Write your rollback migrations here."""
    
    migrator.remove_model('events')

    migrator.remove_model('urls')

    migrator.remove_model('users')

    migrator.remove_model('basemodel')
