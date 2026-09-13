import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from app import handler


def test_returns_default_greeting_when_no_name_given():
    # Arrange
    event = {"queryStringParameters": None, "rawPath": "/hello"}

    # Act
    response = handler(event, None)
    body = json.loads(response["body"])

    # Assert
    assert response["statusCode"] == 200
    assert body["message"] == "Hello, World!"


def test_returns_personalized_greeting_when_name_given():
    # Arrange
    event = {"queryStringParameters": {"name": "Taro"}, "rawPath": "/hello"}

    # Act
    response = handler(event, None)
    body = json.loads(response["body"])

    # Assert
    assert body["message"] == "Hello, Taro!"
