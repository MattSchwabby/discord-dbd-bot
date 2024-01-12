import os
import boto3
import botocore
from boto3.dynamodb.conditions import Key
#from botocore.vendored import requests
import requests
from datetime import datetime
from decimal import Decimal
import json

def get_steam_username(api_key, user_id):
    base_url = "http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/"
    url = f"{base_url}?key={api_key}&steamids={user_id}"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200 and data.get("response", {}).get("players"):
            username = data["response"]["players"][0].get("personaname")
            return username
        else:
            print(f"Error: {data.get('message', 'Unknown error')}")
            return None
    except Exception as e:
        print(f"Error: {e}")
        return None
    
def scan_and_filter_latest_entries(table_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)

    # Scan the entire table
    response = table.scan()

    # Create a dictionary to store the latest items for each SteamUserID
    latest_items = {}

    # Iterate through the scanned items
    for item in response['Items']:
        steam_user_id = item['SteamUserID']
        last_updated = item['lastUpdated']
        steam_user_name = item['SteamUserName']

        # Check if the SteamUserID is already in the dictionary
        if steam_user_id in latest_items:
            # Compare the lastUpdated date to determine if it's more recent
            if datetime.fromisoformat(last_updated) > datetime.fromisoformat(latest_items[steam_user_id]['lastUpdated']):
                # Update the dictionary with the more recent item
                latest_items[steam_user_id] = item
        else:
            # If SteamUserID is not in the dictionary, add it
            latest_items[steam_user_id] = item

    # Convert the dictionary values to a list, including lastUpdated and SteamUserName fields
    result = [
        {
            'SteamUserID': item['SteamUserID'],
            'lastUpdated': item['lastUpdated'],
            'SteamUserName': item['SteamUserName']
        }
        for item in latest_items.values()
    ]

    return result

def handler(event, context):
    USER_CACHE_TABLE = os.environ['USER_CACHE_TABLE']
    steam_api_key = os.environ['steamapikey']

    dynamodb = boto3.resource('dynamodb')
    user_table = dynamodb.Table(USER_CACHE_TABLE)

    latest_users=scan_and_filter_latest_entries(USER_CACHE_TABLE)

    for item in latest_users:
        steam_user_id = item.get('SteamUserID')
        #print(steam_user_id)
        app_id=381210
        steam_username=get_steam_username(steam_api_key,steam_user_id)
        today = datetime.now()
        # Get current ISO 8601 datetime in string format
        iso_date = today.isoformat()
        item = {
            'SteamUserID': int(steam_user_id),
            'SteamUserName': steam_username,
            'DiscordUserID': None,
            'lastUpdated': iso_date
        }
        user_table.put_item(Item=item)
    return {
        'statusCode': 200,
        'body': 'Function executed successfully!'
}