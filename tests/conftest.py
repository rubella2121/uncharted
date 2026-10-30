"""Shared fixtures. Tests run against mongomock (an in-memory fake), so they need no
network and no Atlas account. mongomock enforces unique indexes but NOT $jsonSchema
validators; validator behaviour is verified against real Atlas with `guard doctor`."""
import mongomock
import pytest

from guard import db as dbmod


@pytest.fixture
def db():
    database = mongomock.MongoClient(tz_aware=True)["test_guard"]
    dbmod.ensure_schema(database)
    return database
