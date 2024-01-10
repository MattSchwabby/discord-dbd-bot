import os
import boto3
import requests

def get_dbd_player_stats(api_key, user_id, stat_name):
    # Steam API endpoint for GetPlayerSummaries
    endpoint = "http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/"

    # Dead by Daylight app ID
    app_id = 381210

    # Construct the URL for the API request
    url = f"{endpoint}?key={api_key}&steamid={user_id}&appid={app_id}"

    if(stat_name=="total_wins"):
        try:
            response = requests.get(url)
            data = response.json()
            # Check if the request was successful
            if response.status_code == 200:
                # Search for the DBD_Escape stat in the player stats
                for stat in data["playerstats"]["stats"]:
                    if stat["name"] == "DBD_Escape":
                        DBD_Escape = stat["value"]
                    elif stat["name"] == "DBD_EscapeKO":
                        DBD_EscapeKO = stat["value"]
                    elif stat["name"] == "DBD_EscapeThroughHatch":
                        DBD_EscapeThroughHatch = stat["value"]
                        
                win_value = DBD_Escape + DBD_EscapeKO + DBD_EscapeThroughHatch
                return win_value
                
                # If the stat is not found, return None
                return None
            else:
                print(f"Error: {data['error']['errorMsg']}")
                return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    else:
        try:
            # Make the API request
            response = requests.get(url)
            data = response.json()

            # Check if the request was successful
            if response.status_code == 200:
                # Search for the DBD_Escape stat in the player stats
                for stat in data["playerstats"]["stats"]:
                    
                
                # If the stat is not found, return None
                return None
            else:
                print(f"Error: {data['error']['errorMsg']}")
                return None
        except Exception as e:
            print(f"Error: {e}")
            return None

def handler(event, context):
    # Load environment variables
    dynamo_db_table_name = os.environ['USER_ID_TABLE']
    steam_api_key = os.environ['steamapikey']

    # Create DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(dynamo_db_table_name)

    # Scan User_ID table for all items
    response = table.scan()
    items = response.get('Items', [])

    # Loop through each item and call Steam API
    for item in items:
        steam_user_id = item.get('SteamUserID')
        
        # Call Steam API URL
        steam_api_url = f"http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/?key={steam_api_key}&steamids={steam_user_id}"
        
        try:
            # Make API request
            api_response = requests.get(steam_api_url)
            api_data = api_response.json()

            # Process the API response
            # Example: Print the API data
            print(f"SteamUserID: {steam_user_id}, API Response: {api_data}")

            # Additional processing based on API response
            # ...

        except Exception as e:
            print(f"Error calling Steam API for SteamUserID {steam_user_id}: {e}")

    return {
        'statusCode': 200,
        'body': 'Execution completed successfully'
    }