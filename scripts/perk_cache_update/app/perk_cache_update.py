import json
import boto3
import botocore
#from botocore.vendored import requests
import requests
import os
from datetime import datetime
api_url = 'https://dbd.tricky.lol/api/perks'
perk_url = 'https://dbd.tricky.lol/api/perkinfo'

# DynamoDB configuration
dynamodb = boto3.resource('dynamodb') 
table_name="dbdPerkCache"
table = dynamodb.Table(table_name)

def get_perks_data():
    response = requests.get(api_url)
    return response.json()

def handler(event, context):

    perks_data = get_perks_data()
    today = datetime.now()

    # Get current ISO 8601 datetime in string format
    iso_date = today.isoformat()
    for perk in perks_data.keys():
        name=perks_data[perk]['name']
        item = {
        'perk_id': perk,
        'name': name,
        'lastUpdated': iso_date
        }
        try:
            table.put_item(Item=item)
            print(f"Wrote item {item} to Dynamo")
        except Exception as write_e:
            print(f"Error writing item {item}: {write_e}")


    return {
        'statusCode': 200,
        'body': 'Function executed successfully!'
}

'''
test_event = {
    "key1": "value1",
    "key2": "value2",
    "key3": "value3"
}

context="testing handler()"

handler(test_event, context)
'''