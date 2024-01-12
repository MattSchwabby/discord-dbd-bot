import os
import boto3
import botocore
#from botocore.vendored import requests
import requests
from datetime import datetime
from decimal import Decimal
import json

def get_dbd_player_stats(api_key, user_id):
    # Steam API endpoint for GetPlayerSummaries
    endpoint = "http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/"
    app_id = 381210

    # Construct the URL for the API request
    url = f"{endpoint}?key={api_key}&steamid={user_id}&appid={app_id}"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            return data["playerstats"]["stats"]
    except:
        return "Error getting data from Steam"

# DBD Stat API from Steam
def get_dbd_survivor_wins(api_key, user_id):
    endpoint = "http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/"
    app_id = 381210
    url = f"{endpoint}?key={api_key}&steamid={user_id}&appid={app_id}"
    try:
        response = requests.get(url)
        data = response.json()
        if response.status_code == 200:
            for stat in data["playerstats"]["stats"]:
                if stat["name"] == "DBD_Escape":
                    DBD_Escape = stat["value"]
                elif stat["name"] == "DBD_EscapeKO":
                    DBD_EscapeKO = stat["value"]
                elif stat["name"] == "DBD_EscapeThroughHatch":
                    DBD_EscapeThroughHatch = stat["value"]
                    
            win_value = DBD_Escape + DBD_EscapeKO + DBD_EscapeThroughHatch
            return win_value
    except:
        return "Error getting data from Steam"

def handler(event, context):
    # Load environment variables
    USER_CACHE_TABLE = os.environ['USER_CACHE_TABLE']
    USER_STAT_TABLE = os.environ['USER_STAT_TABLE']
    steam_api_key = os.environ['steamapikey']
    #print(steam_api_key)

    # Create DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    user_table = dynamodb.Table(USER_CACHE_TABLE)
    stat_table = dynamodb.Table(USER_STAT_TABLE)

    # Scan User_ID table for all items
    response = user_table.scan()
    items = response.get('Items', [])
    #print(items)

    for item in items:
        steam_user_id = item.get('SteamUserID')
        #print(steam_user_id)
        app_id=381210
        steam_api_url = f"http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?key={steam_api_key}&steamid={steam_user_id}&appid={app_id}"
        #print(steam_api_url)
        
        try:
            api_response = requests.get(steam_api_url)
            #print(api_response)
            api_data = api_response.json()
            #print(api_data)

            if api_response.status_code == 200:
                #print(f"SteamUserID: {steam_user_id}, API Response: {api_data['playerstats']['stats']}")
                print(steam_user_id)
                stats = json.dumps(api_data['playerstats']['stats'])
                today = datetime.now()

                # Get current ISO 8601 datetime in string format
                iso_date = today.isoformat()
                
                item={
                    'SteamUserID':Decimal(steam_user_id),
                    'date': iso_date,
                    'stats': stats
                }
                
                try:
                    stat_table.put_item(Item=item)
                except Exception as write_e:
                    print(f"Error writing user stats for SteamUserID {steam_user_id}: {write_e}")

                    #print(item)
                #print(item)
        except Exception as e:
            print(f"Error calling Steam API for SteamUserID {steam_user_id}: {e}")
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