#!/usr/bin/env python3
"""
Create ScyllaDB tables via Alternator (DynamoDB-compatible API).

This script creates the tables required for chat history and session management
using ScyllaDB's Alternator API, which is compatible with boto3 DynamoDB clients.
"""

import boto3
from botocore.exceptions import ClientError
import sys


def create_tables():
    """Create chat history tables in ScyllaDB via Alternator."""
    
    # Connect to ScyllaDB Alternator endpoint
    # For local development, use Traefik IngressRoute
    dynamodb = boto3.resource(
        'dynamodb',
        endpoint_url='http://scylla.local',
        region_name='us-east-1',
        aws_access_key_id='none',  # Alternator doesn't require real credentials
        aws_secret_access_key='none',
    )
    
    tables_created = []
    
    # 1. Sessions table
    print("Creating devassist-sessions table...")
    try:
        sessions_table = dynamodb.create_table(
            TableName='devassist-sessions',
            KeySchema=[
                {'AttributeName': 'session_id', 'KeyType': 'HASH'},  # Partition key
            ],
            AttributeDefinitions=[
                {'AttributeName': 'session_id', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',  # On-demand pricing
        )
        print(f"✅ Created table: devassist-sessions")
        tables_created.append('devassist-sessions')
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table already exists: devassist-sessions")
        else:
            print(f"❌ Error creating devassist-sessions: {e}")
            sys.exit(1)
    
    # 2. History table (with sort key for time-series queries)
    print("\nCreating devassist-history table...")
    try:
        history_table = dynamodb.create_table(
            TableName='devassist-history',
            KeySchema=[
                {'AttributeName': 'session_id', 'KeyType': 'HASH'},   # Partition key
                {'AttributeName': 'created_on', 'KeyType': 'RANGE'},  # Sort key (timestamp)
            ],
            AttributeDefinitions=[
                {'AttributeName': 'session_id', 'AttributeType': 'S'},
                {'AttributeName': 'created_on', 'AttributeType': 'S'},
            ],
            BillingMode='PAY_PER_REQUEST',
        )
        print(f"✅ Created table: devassist-history")
        tables_created.append('devassist-history')
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"⚠️  Table already exists: devassist-history")
        else:
            print(f"❌ Error creating devassist-history: {e}")
            sys.exit(1)
    
    print(f"\n{'='*60}")
    print(f"✅ ScyllaDB tables setup complete!")
    print(f"{'='*60}")
    
    if tables_created:
        print(f"\nTables created: {', '.join(tables_created)}")
    
    print("\n📊 Table Schema:")
    print("\n1. devassist-sessions (session metadata)")
    print("   - Primary Key: session_id (HASH)")
    print("   - Attributes: user_id, blueprint, title, session_state, created_on, modified_on")
    
    print("\n2. devassist-history (chat messages)")
    print("   - Primary Key: session_id (HASH) + created_on (RANGE)")
    print("   - Attributes: message_id, role, content, agent, etc.")
    
    print("\n🔌 Endpoint: http://scylla.local")
    print("📝 API: DynamoDB-compatible (Alternator)")


if __name__ == '__main__':
    print("="*60)
    print("ScyllaDB Table Creation Script")
    print("="*60)
    print("\nConnecting to ScyllaDB Alternator API...")
    print("Endpoint: http://scylla.local\n")
    
    try:
        create_tables()
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
