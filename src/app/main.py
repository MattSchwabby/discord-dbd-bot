import os
import boto3
from boto3.dynamodb.conditions import Key
from flask import Flask, jsonify, request
from mangum import Mangum
from asgiref.wsgi import WsgiToAsgi
from discord_interactions import verify_key_decorator
import requests
from datetime import datetime
import re
import time

# Variables
steamapikey = os.environ['steamapikey']
DISCORD_PUBLIC_KEY = os.environ['DISCORD_PUBLIC_KEY']
dynamodb_table_name = os.environ['USER_CACHE_TABLE']
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(dynamodb_table_name)
PERK_CACHE_TABLE = os.environ['PERK_CACHE_TABLE']
perk_cache = dynamodb.Table(PERK_CACHE_TABLE)

# Class Definitions
class shrineperk:
    def __init__(self, name, description, bloodpointcost, shardcost):
        self.name = name
        self.description = description
        self.bloodpointcost = bloodpointcost
        self.shardcost = shardcost

class shrineperks:
    def __init__(self, perks):
        self.perks = perks

# Function Definitions
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
    
def get_latest_steam_userid_dynamo(table_name,steam_user_name):
    table = dynamodb.Table(table_name)
    key_condition_expression = Key('SteamUserName').eq(steam_user_name)
    index_name = 'SteamUserNameIndex'
    response = table.query(
        IndexName=index_name,
        KeyConditionExpression=key_condition_expression,
        ScanIndexForward=False,
        Limit=1  # Limit the result to only one item
    )
    if 'Items' in response and len(response['Items']) > 0:
        # The latest item
        latest_item = response['Items'][0]

        # Retrieve the SteamUserName from the latest item
        steam_user_id = latest_item.get('SteamUserID')

    return steam_user_id

def get_perkid_by_name(table_name,perk_name):
    perk_cache_table = dynamodb.Table(table_name)
    key_condition_expression = Key('name').eq(perk_name)
    index_name = 'PerkNameIndex'
    response = perk_cache_table.query(
        IndexName=index_name,
        KeyConditionExpression=key_condition_expression,
        Limit=1  # Limit the result to only one item
    )
    if 'Items' in response and len(response['Items']) > 0:
        # The latest item
        dynamo_response = response['Items'][0]

        # Retrieve the SteamUserName from the latest item
        perk_id = dynamo_response.get('perk_id')

    return perk_id

# DBD Stat API from Steam
def get_dbd_player_stats(api_key, user_id, stat_name):
    # Steam API endpoint for GetPlayerSummaries
    endpoint = "http://api.steampowered.com/ISteamUserStats/GetUserStatsForGame/v0002/"

    # Dead by Daylight app ID
    app_id = 381210

    url = f"{endpoint}?key={api_key}&steamid={user_id}&appid={app_id}"

    if(stat_name=="total_wins"):
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
                
                return None
            else:
                print(f"Error: {data['error']['errorMsg']}")
                return None
        except Exception as e:
            print(f"Error: {e}")
            return None
    else:
        try:
            response = requests.get(url)
            data = response.json()

            if response.status_code == 200:
                for stat in data["playerstats"]["stats"]:
                    if stat["name"] == stat_name:
                        return stat["value"]
                
                return None
            else:
                print(f"Error: {data['error']['errorMsg']}")
                return None
        except Exception as e:
            print(f"Error: {e}")
            return None

def replace_numbers_in_description(json_data):
    description = json_data["description"]
    tunables = json_data["tunables"]

    for index, values in enumerate(tunables):
        placeholder = "{" + str(index) + "}"
        if len(values) == 1:
            replacement = "**" + values[0] + "**"
        else:
            replacement = ", ".join(f"**{v}**" for v in values)
        description = description.replace(placeholder, replacement)

    json_data["description"] = description
    return json_data

def replace_html_tags(input_string):
    # Replace <b> and </b> with **
    result_string = input_string.replace('<b>', '**').replace('</b>', '**')
    
    # Replace <i> and </i> with *
    result_string = result_string.replace('<i>', '*').replace('</i>', '*')
    
    # Replace <br> with \n
    result_string = result_string.replace('<br>', '\n')

    # Replace <br><br> with \n
    result_string = result_string.replace('<br><br>', '\n')
    
    # Remove <ul> and </ul>
    result_string = result_string.replace('<ul>', '').replace('</ul>', '').replace('</li>', '')
    
    # Replace <li> and </li> with -
    result_string = result_string.replace('<li>', ' - ')
    
    return result_string

def scan_table_and_filter_latest_items(table_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    response = table.scan()
    latest_items = {}
    for item in response['Items']:
        steam_user_id = item['SteamUserID']
        steam_user_name = item['SteamUserName']
        date = item['lastUpdated']
        if steam_user_name in latest_items:
            if datetime.fromisoformat(date) > datetime.fromisoformat(latest_items[steam_user_name]['lastUpdated']):
                latest_items[steam_user_name] = item
        else:
            latest_items[steam_user_name] = item
    result = list(latest_items.values())
    return result

          
# DBD Stat Description Dictionary
descriptors = {
'total_wins': 'The total number of times you\'ve escaped as a survivor',
"DBD_HookedAndEscape": 'The number of times you\'ve escaped after unhooking yourself',
"DBD_Chapter9_Camper_Stat1": 'The number of times you unhooked yourself',
'DBD_EscapeKO': 'The number of times you\'ve escaped while crawling (downed) as a survivor',
'DBD_CamperSkulls': 'Your current season rank as a survivor',
'DBD_GeneratorPct_float': "The number of generators you\'ve repaired",
"DBD_DLC7_Camper_Stat2": 'The number of exit gates you\'ve opened',
"DBD_Chapter15_Camper_Stat1": "The number of survivors you\'ve recovered from the dying/downed state",
'DBD_UnhookOrHeal_PostExit': "The number of Survivors you\'ve unhooked or healed from dying state in endgame",
"DBD_Camper9_Stat2": "Number of times you\'ve escaped after been injured for half of the trail",
"DBD_Camper8_Stat2": 'The number of times you\'ve vaulted while in a chase',
"DBD_Chapter12_Camper_Stat2": "The number of times you\'ve escaped through the hatch while crawling/downed",
"DBD_DLC3_Camper_Stat1": "The number of Hex totems you\'ve cleansed",
"DBD_HitNearHook": "The number of protection hits you\'ve taken for a survivor that was just unhooked",
"DBD_DLC8_Camper_Stat1": "The number of times you\'ve escaped after getting downed once",
"DBD_DLC9_Camper_Stat1": "Number of successful vaults that made the killer miss",
"DBD_Chapter11_Camper_Stat1_float": "The number of survivors you\'ve healed while injured",
"DBD_Chapter14_Camper_Stat1": "How mant Protection hits you\'ve taken while the killer was carrying a survivor",
'DBD_HealPct_float': "The number of survivors you\'ve healed",
"DBD_SkillCheckSuccess":'The number of skill checks you\'ve succeeded',
"DBD_CamperMaxScoreByCategory": 'Survivor perfect games (5k+ Bloodpoints in all categories)',
'DBD_Escape': 'The number of times you\'ve escaped while injured as a survivor',
'DBD_EscapeThroughHatch': 'The number of times you\'ve escaped through the hatch',
"DBD_AllEscapeThroughHatch":'The number of times you\'re entire team has escaped through the hatch to win a match.',
"DBD_EscapeNoBlood_MapAsy_Asylum": 'Escaped from Crotus Prenn Asylum with no bloodloss',
"DBD_FixSecondFloorGenerator_MapAsy_Asylum": 'Repaired 2nd floor generator and escaped from Disturbed Ward',
"DBD_FixSecondFloorGenerator_MapSub_Street": 'Repaired Myers\' house generator and escaped from Lampkin Lane',
"DBD_FixSecondFloorGenerator_MapBrl_MaHouse": 'Repaired dwelling generator and escaped from Mother\'s Dwelling (The generator in the middle building of Red Forest)',
"DBD_FixSecondFloorGenerator_MapFin_Hideout": 'Repaired bathroom generator and escaped from The Game (Generator in the bathroom in the lower floor of Gideon)',
"DBD_FixSecondFloorGenerator_MapKny_Cottage": 'Repaired chalet generator and escaped from Mount Ormond Resort',
"DBD_FixSecondFloorGenerator_MapBrl_Temple": 'Repaired temple basement generator and escaped from The Temple of Purgation',
"DBD_FixSecondFloorGenerator_MapQat_Lab": 'Repaired isolation room generator and escaped from The Underground Complex',
"DBD_FixSecondFloorGenerator_MapHti_Shrine": 'Repaired upper shrine generator and escaped from Sanctum of Wrath',
"DBD_FixSecondFloorGenerator_MapUkr_Saloon": 'Repaired saloon generator and escaped from Dead Dawg Saloon',
'DBD_KillerSkulls': 'Your current season rank as a killer',
'DBD_KilledCampers': 'The number of survivors you\'ve killed (Mori, Devour Hope, Rancor, Pig Traps, etc.)',
"DBD_SacrificedCampers": 'The number of survivors you\'ve sacrificed (killed on the hook)',
"DBD_Chapter11_Slasher_Stat1": 'The number of times you\'ve wiped a team of survivors (sacrificed all survivors before the last generator is repaired)',
"DBD_DLC8_Slasher_Stat2": 'Survivors killed or sacrificed after all generators are repaired',
"DBD_Chapter12_Slasher_Stat1": 'Survivors grabbed while repairing a generator',
"DBD_DLC6_Slasher_Stat2": 'Survivors hooked in the basement (once per survivor)',
"DBD_DLC7_Slasher_Stat2": 'Obsessions sacrificed',
"DBD_Event1_Stat1": 'Had at least 3 survivors hooked in the basement at same time',
"DBD_DLC9_Slasher_Stat1": 'Generators damaged with a survivor hooked',
"DBD_Chapter9_Slasher_Stat1": 'Hit a survivor who dropped a pallet within a chase',
"DBD_Chapter10_Slasher_Stat1": 'Hit a survivor while carrying another',
"DBD_Chapter10_Camper_Stat1": 'Hooks broken',
"DBD_Chapter15_Slasher_Stat2": 'Survivors grabbed while cleansing a totem',
"DBD_Chapter13_Slasher_Stat1": 'Hatches closed',
"DBD_Chapter14_Slasher_Stat1": 'Hooked a survivor while everyone is injured',
"DBD_SlasherMaxScoreByCategory":'Killer perfect games (5k+ Bloodpoints in all categories)',
"DBD_TrapPickup": "The number of survivors you\'ve caught in a trap as Trapper",
"DBD_UncloakAttack": 'Number of times you\'ve attacked a survivor after uncloaking as Wraith',
'DBD_SlasherChainAttack': 'Blink attacks (nurse)',
'DBD_Chapter12_Slasher_Stat2': 'Downed survivors while marked (ghostface)',
'DBD_SlasherTierIncrement': 'Evil Within tiers ups (myers)',
'DBD_DLC3_Slasher_Stat1': 'Phantasms triggered (hag)',
'DBD_DLC4_Slasher_Stat1': 'Shocks (doctor)',
'DBD_DLC5_Slasher_Stat1': 'Hatchets thrown (huntress)',
'DBD_DLC6_Slasher_Stat1': 'Downed survivors with chainsaw (leatherface)',
'DBD_DLC8_Slasher_Stat1': 'Reverse bear traps placed (pig)',
'DBD_Chapter10_Slasher_Stat2': 'Downed survivors while in deep wound (legion)',
'DBD_Chapter11_Slasher_Stat2': 'Downed survivors while in max sickness (plague)',
'DBD_Chapter13_Slasher_Stat2': 'Downed survivors using shred (demogorgon)',
'DBD_Chapter14_Slasher_Stat2': 'Downed survivors while using blood fury (oni)',
'DBD_Chapter15_Slasher_Stat1': 'Downed survivors while speared (deathslinger)',
"DBD_BloodwebPoints":'Total bloodpoints you\'ve earned'
}

overallstats=[
"total_wins",
"DBD_SacrificedCampers",
"DBD_BloodwebPoints",
"DBD_CamperMaxScoreByCategory",
"DBD_SlasherMaxScoreByCategory",
"DBD_CamperSkulls",
'DBD_KillerSkulls']

survivorstats=[
"total_wins",
'DBD_GeneratorPct_float', 
'DBD_HealPct_float',
"DBD_SkillCheckSuccess",
"DBD_CamperMaxScoreByCategory",
"DBD_DLC7_Camper_Stat2",
"DBD_Escape",
'DBD_EscapeThroughHatch',
"DBD_AllEscapeThroughHatch",
'DBD_UnhookOrHeal_PostExit',
"DBD_Camper9_Stat2",
"DBD_Chapter15_Camper_Stat1", 
"DBD_Camper8_Stat2",
"DBD_DLC9_Camper_Stat1",
"DBD_HitNearHook",
"DBD_Chapter12_Camper_Stat2",
"DBD_DLC3_Camper_Stat1",
"DBD_DLC8_Camper_Stat1",
'DBD_Escape',
"DBD_Chapter11_Camper_Stat1_float",
"DBD_Chapter14_Camper_Stat1",
"DBD_HookedAndEscape", 
"DBD_Chapter9_Camper_Stat1", 
"DBD_EscapeKO",
"DBD_BloodwebPoints",
"DBD_CamperSkulls"]

survivormapstats=[
"DBD_EscapeNoBlood_MapAsy_Asylum", 
"DBD_FixSecondFloorGenerator_MapAsy_Asylum", 
"DBD_FixSecondFloorGenerator_MapSub_Street", 
"DBD_FixSecondFloorGenerator_MapBrl_MaHouse", 
"DBD_FixSecondFloorGenerator_MapFin_Hideout", 
"DBD_FixSecondFloorGenerator_MapKny_Cottage", 
"DBD_FixSecondFloorGenerator_MapBrl_Temple",
"DBD_FixSecondFloorGenerator_MapQat_Lab",
"DBD_FixSecondFloorGenerator_MapHti_Shrine",
"DBD_FixSecondFloorGenerator_MapUkr_Saloon"]

killerstats=[
"DBD_SacrificedCampers",
"DBD_Chapter11_Slasher_Stat1",
'DBD_KilledCampers',
"DBD_DLC8_Slasher_Stat2",
"DBD_Chapter12_Slasher_Stat1",
"DBD_DLC6_Slasher_Stat2",
"DBD_DLC7_Slasher_Stat2",
"DBD_Event1_Stat1",
"DBD_DLC9_Slasher_Stat1",
"DBD_Chapter9_Slasher_Stat1",
"DBD_Chapter10_Slasher_Stat1",
"DBD_Chapter10_Camper_Stat1",
"DBD_Chapter15_Slasher_Stat2",
"DBD_Chapter13_Slasher_Stat1",
"DBD_Chapter14_Slasher_Stat1",
"DBD_SlasherMaxScoreByCategory",
'DBD_KillerSkulls']

killercharacterstats=[
"DBD_TrapPickup",
"DBD_UncloakAttack",
'DBD_SlasherChainAttack',
'DBD_Chapter12_Slasher_Stat2',
'DBD_SlasherTierIncrement',
'DBD_DLC3_Slasher_Stat1',
'DBD_DLC4_Slasher_Stat1',
'DBD_DLC5_Slasher_Stat1',
'DBD_DLC6_Slasher_Stat1',
'DBD_DLC8_Slasher_Stat1',
'DBD_Chapter10_Slasher_Stat2',
'DBD_Chapter11_Slasher_Stat2',
'DBD_Chapter13_Slasher_Stat2',
'DBD_Chapter14_Slasher_Stat2',
'DBD_Chapter15_Slasher_Stat1']

# Main

# Initialize the Flask app
app = Flask(__name__)
asgi_app = WsgiToAsgi(app)
handler = Mangum(asgi_app)

# API Routes
@app.route("/", methods=["POST"])
async def interactions():
    print(f"👉 Request: {request.json}")
    raw_request = request.json
    return interact(raw_request)

# Discord Auth
@verify_key_decorator(DISCORD_PUBLIC_KEY)

# Main Function
def interact(raw_request):
    if raw_request["type"] == 1:  
        response_data = {"type": 1}  
    else:
        data = raw_request["data"]
        command_name = data["name"]
        memberinfo = raw_request["member"]
        userinfo = memberinfo["user"]
        username = userinfo["username"]
        globalname = userinfo["global_name"]
        if command_name == "hello":
            message_content = "Hello there!"
        elif command_name == "help":
            message_content = "I look up Dead By Daylight stats from Steam. Here are my commands:\n\n"
            message_content += "**/shrine** - Lists perks in the Shrine of Secrets & cost \nUsage: **/shrine**\n"
            message_content += "**/perk** - Shows description for a given perk name. *Useful after getting perks from **/shrine***\nUsage: **/perk** <Perk Name>"
            message_content += "**/stats** - Shows overall DBD stats, ex: # of matches escaped & # of survivors sacrificed.\nUsage: **/stats <SteamID or username>** (example: */stats Mattschwabby*).\n"
            message_content += "**/survivorstats** - Shows DBD survivor stats, ex.: # of escapes, # of generators repaired.\nUsage: **/survivorstats <SteamIDor username>** (example: */survivorstats 76561197968420961*).\n"
            message_content += "**/survivormapstats** - Shows map-specific survivor statistics.\nUsage: **/survivormapstats <SteamID or username>** (example: */survivormapstats Mattschwabby*).\n"
            message_content += "**/killerstats** - Shows DBD Killer stats, ex: # of survivors hooked, # of survivors killed.\nUsage: **/killerstats <SteamID or username>** (example: */killerstats 76561197968420961*).\n"
            message_content += "**/killercharacterstats** - Shows killer-specific stats.\nUsage: **/killercharacterstats <SteamID or username>** (example: */killercharacterstats Mattschwabby*).\n"
            message_content += "**/spookyboys** - Shows cached users including Steam Username & SteamID - updates hourly.\nUsage: **/spookyboys**\n"
            message_content += "\nUsername is case sensitive. Username will only work **after you've sent at least one command with your SteamID**. A SteamID is a unique identifier that's 17 numbers long and **different than your username**. To look up your SteamID, open Steam, click your username in the upper right hand corner, click 'Account Details'. Your Steam ID is below your username.\n"
            message_content += "**Important:** Your Steam Profile & Game details must be public to get your information from Steam. To set your profile to public, open your profile in Steam and click \"Edit Profile\", then set \"My profile\" & \"Game details\" to Public ([Click here for examples of how to look up your SteamID & set your profile to public](https://imgur.com/a/Xw3KbJ5))."
        elif command_name == "steamtest":
            message_sender = data["id"]
            steamuserid = data["options"][0]["value"]
            spacecheck = bool(re.search(r"\s", steamuserid))
            if spacecheck==True:
                message_content = "SteamID must be a number with no spaces. To learn how to find your SteamID, type the **/help** command."
            elif steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                message_content = f"Steam username for SteamID {steamuserid} is {steamusername}"                    
                today = datetime.now()
                # Get current ISO 8601 datetime in string format
                iso_date = today.isoformat()
                print(f"Log from local desktop - SteamID is {steamuserid}, username is {steamusername}, message_content is:")
                print(message_content)
                item = {
                'SteamUserID': int(steamuserid),
                'SteamUserName': steamusername,
                'DiscordUserID': message_sender,
                'lastUpdated': iso_date
            }
                table.put_item(Item=item)
            else:
                message_content = "SteamID must be a number with no spaces. To learn how to find your SteamID, type the **/help** command."
        elif command_name == "survivorstats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            if steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                today = datetime.now()
                # Get current ISO 8601 datetime in string format
                iso_date = today.isoformat()
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'lastUpdated': iso_date
                }
                table.put_item(Item=item)
                result_string=f"Survivor stats for Steam Username **{steamusername}** requested by **@{username}** *(User ID: {steamuserid}*): \n"
                thissurvivorstat=[]
                for stat in survivorstats:
                    teststatresult = get_dbd_player_stats(steamapikey, steamuserid, stat)
                    thissurvivorstat
                    this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                    result_string += this_message
                    print(f"Log from local desktop - stat is {stat}, message_content is:")
                    print(this_message)
                message_content = result_string
            elif steamuserid:
                steam_user_name=steamuserid
                message_sender = data["id"]
                try:
                    steam_user_id=get_latest_steam_userid_dynamo(dynamodb_table_name,steam_user_name)
                    print(f"Received input with alpha characters, searching for steam user id for steam username {steam_user_name} - got {steam_user_id}")
                    today = datetime.now()
                    # Get current ISO 8601 datetime in string format
                    iso_date = today.isoformat()
                    item = {
                        'SteamUserID': int(steam_user_id),
                        'SteamUserName': steam_user_name,
                        'DiscordUserID': message_sender,
                        'lastUpdated': iso_date
                    }
                    table.put_item(Item=item)
                    result_string=f"Survivor stats for Steam Username **{steam_user_name}** requested by **@{username}** *(User ID: {steam_user_id}*): \n"
                    thissurvivorstat=[]
                    for stat in survivorstats:
                        teststatresult = get_dbd_player_stats(steamapikey, steam_user_id, stat)
                        thissurvivorstat
                        this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                        result_string += this_message
                        print(f"Log from local desktop - stat is {stat}, message_content is:")
                        print(this_message)
                    message_content = result_string
                except Exception as e:
                    error_message=f"Couldn't resolve SteamUserID for SteamUserName {steam_user_name}"
                    print(error_message)
                    message_content =error_message
        elif command_name == "survivormapstats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            if steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                today = datetime.now()
                # Get current ISO 8601 datetime in string format
                iso_date = today.isoformat()
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'lastUpdated': iso_date
                }
                table.put_item(Item=item)
                result_string=f"Survivor map stats for Steam Username **{steamusername}** requested by **@{username}** *(User ID: {steamuserid})*: \n"
                thissurvivorstat=[]
                for stat in survivormapstats:
                    teststatresult = get_dbd_player_stats(steamapikey, steamuserid, stat)
                    thissurvivorstat
                    this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                    result_string += this_message
                    print(f"Log from local desktop - stat is {stat}, message_content is:")
                    print(this_message)
                message_content = result_string
            elif steamuserid:
                steam_user_name=steamuserid
                message_sender = data["id"]
                try:
                    steam_user_id=get_latest_steam_userid_dynamo(dynamodb_table_name,steam_user_name)
                    print(f"Received input with alpha characters, searching for steam user id for steam username {steamuserid} - got {steam_user_id}")
                    today = datetime.now()
                    # Get current ISO 8601 datetime in string format
                    iso_date = today.isoformat()
                    item = {
                        'SteamUserID': int(steam_user_id),
                        'SteamUserName': steam_user_name,
                        'DiscordUserID': message_sender,
                        'lastUpdated': iso_date
                    }
                    table.put_item(Item=item)
                    result_string=f"Survivor map stats for Steam Username **{steam_user_name}** requested by **@{username}** *(User ID: {steam_user_id}*): \n"
                    thissurvivorstat=[]
                    for stat in survivormapstats:
                        teststatresult = get_dbd_player_stats(steamapikey, steam_user_id, stat)
                        thissurvivorstat
                        this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                        result_string += this_message
                        print(f"Log from local desktop - stat is {stat}, message_content is:")
                        print(this_message)
                    message_content = result_string
                except Exception as e:
                    error_message=f"Couldn't resolve SteamUserID for SteamUserName {steam_user_name}. Make sure you've sent me **at least one command with your SteamID** before I can find your stats using a **username**. Type /help for instructions on finding your Steam ID."
                    print(error_message)
                    message_content =error_message
        elif command_name == "killerstats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            if steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                today = datetime.now()
                # Get current ISO 8601 datetime in string format
                iso_date = today.isoformat()
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'lastUpdated': iso_date
                }
                table.put_item(Item=item)
                result_string=f"Killer stats for Steam Username **{steamusername}** requested by **@{username}** (User ID: {steamuserid}): \n"
                thissurvivorstat=[]
                for stat in killerstats:
                    teststatresult = get_dbd_player_stats(steamapikey, steamuserid, stat)
                    thissurvivorstat
                    this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                    result_string += this_message
                    print(f"Log from local desktop - stat is {stat}, message_content is:")
                    print(this_message)
                message_content = result_string
            elif steamuserid:
                steam_user_name=steamuserid
                message_sender = data["id"]
                try:
                    steam_user_id=get_latest_steam_userid_dynamo(dynamodb_table_name,steam_user_name)
                    print(f"Received input with alpha characters, searching for steam user id for steam username {steamuserid} - got {steam_user_id}")
                    today = datetime.now()
                    # Get current ISO 8601 datetime in string format
                    iso_date = today.isoformat()
                    item = {
                        'SteamUserID': int(steam_user_id),
                        'SteamUserName': steam_user_name,
                        'DiscordUserID': message_sender,
                        'lastUpdated': iso_date
                    }
                    table.put_item(Item=item)
                    result_string=f"Killer stats for Steam Username **{steam_user_name}** requested by **@{username}** *(User ID: {steam_user_id}*): \n"
                    thissurvivorstat=[]
                    for stat in killerstats:
                        teststatresult = get_dbd_player_stats(steamapikey, steam_user_id, stat)
                        thissurvivorstat
                        this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                        result_string += this_message
                        print(f"Log from local desktop - stat is {stat}, message_content is:")
                        print(this_message)
                    message_content = result_string
                except Exception as e:
                    error_message=f"Couldn't resolve SteamUserID for SteamUserName {steam_user_name}. Make sure you've sent me **at least one command with your SteamID** before I can find your stats using a **username**. Type /help for instructions on finding your Steam ID."
                    print(error_message)
                    message_content =error_message
        elif command_name == "killercharacterstats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            if steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                today = datetime.now()
                # Get current ISO 8601 datetime in string format
                iso_date = today.isoformat()
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'lastUpdated': iso_date
                }
                table.put_item(Item=item)
                result_string=f"Killer character stats for Steam Username **{steamusername}** requested by **@{username}** *(User ID: {steamuserid})*: \n"
                thissurvivorstat=[]
                for stat in killercharacterstats:
                    teststatresult = get_dbd_player_stats(steamapikey, steamuserid, stat)
                    thissurvivorstat
                    this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                    result_string += this_message
                    print(f"Log from local desktop - stat is {stat}, message_content is:")
                    print(this_message)
                message_content = result_string
            elif steamuserid:
                steam_user_name=steamuserid
                message_sender = data["id"]
                try:
                    steam_user_id=get_latest_steam_userid_dynamo(dynamodb_table_name,steam_user_name)
                    print(f"Received input with alpha characters, searching for steam user id for steam username {steamuserid} - got {steam_user_id}")
                    today = datetime.now()
                    # Get current ISO 8601 datetime in string format
                    iso_date = today.isoformat()
                    item = {
                        'SteamUserID': int(steam_user_id),
                        'SteamUserName': steam_user_name,
                        'DiscordUserID': message_sender,
                        'lastUpdated': iso_date
                    }
                    table.put_item(Item=item)
                    result_string=f"Killer character stats for Steam Username **{steam_user_name}** requested by **@{username}** *(User ID: {steam_user_id}*): \n"
                    thissurvivorstat=[]
                    for stat in killercharacterstats:
                        teststatresult = get_dbd_player_stats(steamapikey, steam_user_id, stat)
                        thissurvivorstat
                        this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                        result_string += this_message
                        print(f"Log from local desktop - stat is {stat}, message_content is:")
                        print(this_message)
                    message_content = result_string
                except Exception as e:
                    error_message=f"Couldn't resolve SteamUserID for SteamUserName {steam_user_name}. Make sure you've sent me **at least one command with your SteamID** before I can find your stats using a **username**. Type /help for instructions on finding your Steam ID."
                    print(error_message)
                    message_content =error_message
        elif command_name == "stats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            if steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                today = datetime.now()
                # Get current ISO 8601 datetime in string format
                iso_date = today.isoformat()
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'lastUpdated': iso_date
                }
                table.put_item(Item=item)
                result_string=f"Overall stats for Steam Username **{steamusername}** requested by **@{username}** *(User ID: {steamuserid}*): \n"
                thissurvivorstat=[]
                for stat in overallstats:
                    teststatresult = get_dbd_player_stats(steamapikey, steamuserid, stat)
                    #thissurvivorstat
                    this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                    result_string += this_message
                    print(f"Log from main.py - stat is {stat}, message_content is:")
                    print(this_message)
                message_content = result_string
            elif steamuserid:
                steam_user_name=data["options"][0]["value"]
                message_sender = data["id"]
                try:
                    steam_user_id=get_latest_steam_userid_dynamo(dynamodb_table_name,steam_user_name)
                    print(f"Received input with alpha characters, searching for steam user id for steam username {steamuserid} - got {steam_user_id}")
                    today = datetime.now()
                    # Get current ISO 8601 datetime in string format
                    iso_date = today.isoformat()
                    item = {
                        'SteamUserID': int(steam_user_id),
                        'SteamUserName': steam_user_name,
                        'DiscordUserID': message_sender,
                        'lastUpdated': iso_date
                    }
                    table.put_item(Item=item)
                    result_string=f"Overall stats for Steam Username **{steam_user_name}** requested by **@{username}** *(User ID: {steam_user_id}*): \n"
                    thissurvivorstat=[]
                    for stat in overallstats:
                        teststatresult = get_dbd_player_stats(steamapikey, steam_user_id, stat)
                        thissurvivorstat
                        this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                        result_string += this_message
                        print(f"Log from local desktop - stat is {stat}, message_content is:")
                        print(this_message)
                    message_content = result_string
                except Exception as e:
                    error_message=f"Couldn't resolve SteamUserID for SteamUserName {steam_user_name}. Make sure you've sent me **at least one command with your SteamID** before I can find your stats using a **username**. Type /help for instructions on finding your Steam ID."
                    print(error_message)
                    message_content =error_message
        elif command_name == "shrine":
            try:
                shrineurl="https://dbd.tricky.lol/api/shrine"
                shrineperkurl="https://dbd.tricky.lol/api/perkinfo"
                shrineresponse = requests.get(shrineurl)
                perks = shrineresponse.json()
                result_string=f"Current shrine perks are: \n"
                for perk in perks["perks"]:
                    thisperk=perk["id"]
                    thisperkurl=f"{shrineperkurl}?perk={thisperk}"
                    perkresponse=requests.get(thisperkurl)
                    thisperkinfo = perkresponse.json()
                    this_shrine_perk=shrineperk(name=thisperkinfo["name"], description=thisperkinfo["description"], bloodpointcost=perk["bloodpoints"], shardcost=perk["shards"])
                    result_string+=f"**{this_shrine_perk.name}** \n Bloodpoint cost: **{this_shrine_perk.bloodpointcost}** \n Shard cost: **{this_shrine_perk.shardcost}** \n"
                result_string+=f"\nYou can look up a Perk's description using the /perk command (Case sensitive): **/perk {this_shrine_perk.name}** "
                print(f"Log from main.py - Discord user {username} requested current shrine perks. message_content: ")
                print(result_string)
                message_content = result_string
            except Exception as e:
                print("User encountered an exception")
                message_content = "Discord encountered an error when processing your request. Please try again."
        elif command_name == "perk":
            perk_name = data["options"][0]["value"]
            perk_id=get_perkid_by_name(PERK_CACHE_TABLE,perk_name)
            message_sender = data["id"]
            perkurl="https://dbd.tricky.lol/api/perkinfo"
            thisperkurl=f"{perkurl}?perk={perk_id}"
            try:
                perkresponse=requests.get(thisperkurl)
                thisperkinfo = perkresponse.json()
                perk_name = thisperkinfo["name"]
                replaced_description=replace_numbers_in_description(thisperkinfo)
                new_description=replace_html_tags(replaced_description["description"])
                message_content=f"**Name:** {perk_name} \n**ID:** {perk_id}\n**Description:** {new_description}"
            except:
                message_content=f"Failed to get Perk information for: {perk_name}. Please try again, and check the spelling of the Perk Name."
        elif command_name == "spookyboys":
            spoooky_boy_result = scan_table_and_filter_latest_items(dynamodb_table_name)
            print(spoooky_boy_result)
            message_content=f"My current user cache is: \n"
            for spooky_boy in spoooky_boy_result:
                message_content+=f"Steam Username: **{spooky_boy['SteamUserName']}** | SteamID: **{spooky_boy['SteamUserID']}** | Last Updated: *{spooky_boy['lastUpdated']}* \n"
            message_content+=f"\nExample command using a username: **/stats {spooky_boy['SteamUserName']}**"
            message_content+=f"\nExample command using a SteamID: **/stats {spooky_boy['SteamUserID']}**"


        # Form the message to be sent to Discord
        response_data = {
            "type": 4,
            "data": {"content": message_content},
        }

    return jsonify(response_data)

# For testing the app locally (run main.py and copy a Discord request from the Cloudwatch logs)
if __name__ == "__main__":
    app.run(debug=True)
