"""Data access layer for persistence."""

from .dynamodb_client import DynamoDBClient, get_dynamodb_client

__all__ = ["DynamoDBClient", "get_dynamodb_client"]
