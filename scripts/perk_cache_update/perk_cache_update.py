import json
import requests
import boto3
import os

api_url = 'https://dbd.tricky.lol/api/perks'

# DynamoDB configuration
dynamodb = boto3.resource('dynamodb') 
table_name = os.environ.get('DYNAMODB_TABLE_NAME')  # Get DynamoDB table name from environment variable
table = dynamodb.Table(table_name)

def get_perks_data():
    response = requests.get(api_url)
    return response.json()

def lambda_handler(event, context):
    perks_data = get_perks_data()

    if 'error' in perks_data:
        return {
            'statusCode': 500,
            'body': json.dumps({'error': perks_data['error']})
        }
    else:
        store_in_dynamodb(perks_data)
        return {
            'statusCode': 200,
            'body': json.dumps({'message': 'Data stored in DynamoDB successfully!'})
        }

def store_in_dynamodb(data):
    for perk in data:
        item = {
            'perk_id': perk['id'],
            'name': perk['name'],
            # Add other fields as needed
        }
        table.put_item(Item=item)