import json
import requests
import boto3
import os
import time
api_url = 'https://dbd.tricky.lol/api/perks'
perk_url = 'https://dbd.tricky.lol/api/perkinfo'

# DynamoDB configuration
dynamodb = boto3.resource('dynamodb') 
table_name="dbdPerkCache"
table = dynamodb.Table(table_name)

def get_perks_data():
    response = requests.get(api_url)
    return response.json()

perks_data = get_perks_data()

for perk in perks_data.keys():
    name=perks_data[perk]['name']
    item = {
    'perk_id': perk,
    'name': name,
    }
    try:
        table.put_item(Item=item)
        print(f"Wrote item {item} to Dynamo")
    except Exception as write_e:
        print(f"Error writing item {item}: {write_e}")


