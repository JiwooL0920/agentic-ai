"""
DynamoDB-compatible client for ScyllaDB Alternator.

ScyllaDB's Alternator API provides DynamoDB compatibility, allowing us to use
standard boto3/aioboto3 libraries with minimal code changes.
"""

import time
from typing import Any

import aioboto3
import structlog
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from ..config import get_settings

logger = structlog.get_logger()
settings = get_settings()


class DynamoDBClient:
    """
    Async DynamoDB-compatible client for ScyllaDB Alternator.

    Provides common operations (put, get, query, update) with connection pooling.
    """

    def __init__(self):
        self._session = aioboto3.Session()
        self._config = Config(
            retries={'max_attempts': 3, 'mode': 'adaptive'},
            connect_timeout=5,
            read_timeout=30,
        )

    def _get_client_params(self) -> dict:
        """Get boto3 client parameters for ScyllaDB Alternator."""
        return {
            'service_name': 'dynamodb',
            'endpoint_url': settings.scylladb_endpoint,
            'region_name': settings.aws_region,
            'aws_access_key_id': settings.aws_access_key_id,
            'aws_secret_access_key': settings.aws_secret_access_key,
            'config': self._config,
        }

    async def put_item(
        self,
        table_name: str,
        item: dict[str, Any],
    ) -> bool:
        """Put item into table."""
        async with self._session.client(**self._get_client_params()) as client:
            try:
                await client.put_item(
                    TableName=table_name,
                    Item=self._serialize_item(item),
                )
                logger.debug("dynamodb_put_success", table=table_name)
                return True
            except (ClientError, BotoCoreError) as e:
                logger.error("dynamodb_put_error", table=table_name, error=str(e))
                raise

    async def get_item(
        self,
        table_name: str,
        key: dict[str, Any],
    ) -> dict[str, Any] | None:
        """Get item by key."""
        async with self._session.client(**self._get_client_params()) as client:
            try:
                response = await client.get_item(
                    TableName=table_name,
                    Key=self._serialize_item(key),
                )
                item = response.get('Item')
                if item:
                    return self._deserialize_item(item)
                return None
            except (ClientError, BotoCoreError) as e:
                logger.error("dynamodb_get_error", table=table_name, error=str(e))
                raise

    async def query(
        self,
        table_name: str,
        partition_key: str,
        partition_value: str,
        index_name: str | None = None,
        sort_ascending: bool = True,
        limit: int | None = None,
        filter_expression: str | None = None,
        filter_values: dict | None = None,
    ) -> list[dict[str, Any]]:
        """
        Query items by partition key.
        """
        async with self._session.client(**self._get_client_params()) as client:
            params = {
                'TableName': table_name,
                'KeyConditionExpression': f'{partition_key} = :pk',
                'ExpressionAttributeValues': {':pk': {'S': partition_value}},
                'ScanIndexForward': sort_ascending,
            }

            if index_name:
                params['IndexName'] = index_name

            if limit:
                params['Limit'] = limit

            if filter_expression and filter_values:
                params['FilterExpression'] = filter_expression
                # Merge filter values into expression attribute values
                for k, v in filter_values.items():
                    params['ExpressionAttributeValues'][k] = self._serialize_value(v)

            try:
                response = await client.query(**params)
                items = response.get('Items', [])
                return [self._deserialize_item(item) for item in items]
            except (ClientError, BotoCoreError) as e:
                logger.error("dynamodb_query_error", table=table_name, error=str(e))
                raise

    async def update_item(
        self,
        table_name: str,
        key: dict[str, Any],
        updates: dict[str, Any],
    ) -> bool:
        """Update item attributes."""
        async with self._session.client(**self._get_client_params()) as client:
            # Build UpdateExpression
            update_parts = []
            attr_names = {}
            attr_values = {}

            for idx, (field, value) in enumerate(updates.items()):
                placeholder_name = f"#f{idx}"
                placeholder_value = f":v{idx}"
                update_parts.append(f"{placeholder_name} = {placeholder_value}")
                attr_names[placeholder_name] = field
                attr_values[placeholder_value] = self._serialize_value(value)

            update_expression = f"SET {', '.join(update_parts)}"

            try:
                await client.update_item(
                    TableName=table_name,
                    Key=self._serialize_item(key),
                    UpdateExpression=update_expression,
                    ExpressionAttributeNames=attr_names,
                    ExpressionAttributeValues=attr_values,
                )
                logger.debug("dynamodb_update_success", table=table_name)
                return True
            except (ClientError, BotoCoreError) as e:
                logger.error("dynamodb_update_error", table=table_name, error=str(e))
                raise

    def _serialize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Convert Python dict to DynamoDB format."""
        return {k: self._serialize_value(v) for k, v in item.items()}

    def _serialize_value(self, value: Any) -> dict[str, Any]:
        """Serialize a single value to DynamoDB format."""
        if isinstance(value, str):
            return {'S': value}
        elif isinstance(value, bool):
            return {'BOOL': value}
        elif isinstance(value, (int, float)):
            return {'N': str(value)}
        elif isinstance(value, list):
            return {'L': [self._serialize_value(v) for v in value]}
        elif isinstance(value, dict):
            return {'M': self._serialize_item(value)}
        elif value is None:
            return {'NULL': True}
        else:
            return {'S': str(value)}

    def _deserialize_item(self, item: dict[str, Any]) -> dict[str, Any]:
        """Convert DynamoDB format to Python dict."""
        return {k: self._deserialize_value(v) for k, v in item.items()}

    def _deserialize_value(self, value: dict[str, Any]) -> Any:
        """Deserialize a single DynamoDB value."""
        if 'S' in value:
            return value['S']
        elif 'N' in value:
            num = value['N']
            return int(num) if '.' not in num else float(num)
        elif 'BOOL' in value:
            return value['BOOL']
        elif 'NULL' in value:
            return None
        elif 'L' in value:
            return [self._deserialize_value(v) for v in value['L']]
        elif 'M' in value:
            return self._deserialize_item(value['M'])
        else:
            return str(value)


# Global client singleton
_dynamodb_client: DynamoDBClient | None = None


def get_dynamodb_client() -> DynamoDBClient:
    """Get or create global DynamoDB client."""
    global _dynamodb_client
    if _dynamodb_client is None:
        _dynamodb_client = DynamoDBClient()
    return _dynamodb_client


def calculate_ttl(days: int) -> int:
    """Calculate Unix timestamp for TTL."""
    return int(time.time()) + (days * 24 * 60 * 60)
