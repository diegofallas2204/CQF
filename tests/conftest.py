"""
tests/conftest.py

Fixtures para tests unitarios y de integración.
"""
import pytest
import json
import os

BASE = os.path.join(os.path.dirname(__file__), "fixtures")

@pytest.fixture
def city_fixture():
    path = os.path.join(BASE, "city_fixture.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

@pytest.fixture
def orders_fixture():
    path = os.path.join(BASE, "orders_fixture.json")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)