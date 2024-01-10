import os
import boto3
from flask import Flask, jsonify, request
from mangum import Mangum
from asgiref.wsgi import WsgiToAsgi
from discord_interactions import verify_key_decorator
import requests
import datetime
import re

# Variables
steamapikey = os.environ['steamapikey']
DISCORD_PUBLIC_KEY = os.environ['DISCORD_PUBLIC_KEY']
dynamodb_table_name = os.environ['DYNAMODB_TABLE_NAME']
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table(dynamodb_table_name)

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
        for value in values:
            placeholder = "{" + str(index) + "}"
            replacement = "**" + value + "**"
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
    
    # Remove <ul> and </ul>
    result_string = result_string.replace('<ul>', '').replace('</ul>', '').replace('</li>', '')
    
    # Replace <li> and </li> with -
    result_string = result_string.replace('<li>', ' - ')
    
    return result_string
          
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
            message_content = "I'm Spooky Bot. I'll look up your Dead By Daylight stats from Steam using your SteamID. Here are my commands:\n\n"
            message_content += "**/shrine** - Looks up the current perks in the Shrine of Secrets and their cost *(doesn't require SteamID.)* \nUsage: **/shrine**\n"
            message_content += "**/perk** - Looks up the description for a given perk ID. *Meant to be used after getting a Perk ID from **/shrine***\nUsage: **/perk** <Perk ID>"
            message_content += "**/stats** - Looks up overall Dead by Daylight stastics, like number of matches escaped as a survivor and number of survivors sacrificed as killer.\nUsage: **/stats <SteamID>** (example: */stats 76561197968420961*).\n"
            message_content += "**/survivorstats** - Looks up Dead By Daylight survivor statistics, ex.: # of games escaped, # of generators repaired.\nUsage: **/survivorstats <SteamID>** (example: */survivorstats 76561197968420961*).\n"
            message_content += "**/survivormapstats** - Looks up map-specific survivor statistics.\nUsage: **/survivormapstats <SteamID>** (example: */survivormapstats 76561197968420961*).\n"
            message_content += "**/killerstats** - Looks up Dead by Daylight Killer statistics, like: # of survivors hooked, # of survivors killed.\nUsage: **/killerstats <SteamID>** (example: */killerstats 76561197968420961*).\n"
            message_content += "**/killercharacterstats** - Looks up character-specific stats as killer.\nUsage: **/killercharacterstats <SteamID>** (example: */killercharacterstats 76561197968420961*).\n"
            message_content += "\nYour SteamID is a unique identifier that's 17 numbers long and **different than your username**. To look up your SteamID, open Steam, click your username in the upper right hand side of the application, select 'Account Details'. Your Steam ID is below your username.\n"
            message_content += "**Important:** Your Steam Profile & Game details must be set to public to get your information from the Steam API. To set your profile to public, open your profile in Steam and click \"Edit Profile\", then set \"My profile\" and \"Game details\" to Public ([Click here for examples of how to look up your SteamID and set your profile to public](https://imgur.com/a/Xw3KbJ5))."
        elif command_name == "steamtest":
            message_sender = data["id"]
            steamuserid = data["options"][0]["value"]
            spacecheck = bool(re.search(r"\s", steamuserid))
            if spacecheck==True:
                message_content = "SteamID must be a number with no spaces. To learn how to find your SteamID, type the **/help** command."
            elif steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                message_content = f"Steam username for SteamID {steamuserid} is {steamusername}"
                print(f"Log from local desktop - SteamID is {steamuserid}, username is {steamusername}, message_content is:")
                print(message_content)
                item = {
                'SteamUserID': int(steamuserid),
                'SteamUserName': steamusername,
                'DiscordUserID': message_sender,
                'DiscordUserName': username,
                'DiscordGlobalName': globalname,
                'lastUpdated': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # Format timestamp as desired
            }
                table.put_item(Item=item)
            else:
                message_content = "SteamID must be a number with no spaces. To learn how to find your SteamID, type the **/help** command."
        elif command_name == "survivorstats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            spacecheck = bool(re.search(r"\s", steamuserid))
            if spacecheck==True:
                message_content = "SteamID must be a number with no spaces. To learn how to find your SteamID, type the **/help** command."
            elif steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'DiscordUserName': username,
                    'DiscordGlobalName': globalname,
                    'lastUpdated': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # Format timestamp as desired
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
        elif command_name == "survivormapstats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            spacecheck = bool(re.search(r"\s", steamuserid))
            if spacecheck==True:
                message_content = "SteamID must be a number with no spaces. To learn how to find your SteamID, type the **/help** command."
            elif steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'DiscordUserName': username,
                    'DiscordGlobalName': globalname,
                    'lastUpdated': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # Format timestamp as desired
                }
                table.put_item(Item=item)
                result_string=f"Survivor stats for Steam Username **{steamusername}** requested by **@{username}** *(User ID: {steamuserid})*: \n"
                thissurvivorstat=[]
                for stat in survivormapstats:
                    teststatresult = get_dbd_player_stats(steamapikey, steamuserid, stat)
                    thissurvivorstat
                    this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                    result_string += this_message
                    print(f"Log from local desktop - stat is {stat}, message_content is:")
                    print(this_message)
                message_content = result_string
        elif command_name == "killerstats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            spacecheck = bool(re.search(r"\s", steamuserid))
            if spacecheck==True:
                message_content = "SteamID must be a number with no spaces. To learn how to find your SteamID, type the **/help** command."
            elif steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'DiscordUserName': username,
                    'DiscordGlobalName': globalname,
                    'lastUpdated': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # Format timestamp as desired
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
        elif command_name == "killercharacterstats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            spacecheck = bool(re.search(r"\s", steamuserid))
            if spacecheck==True:
                message_content = "SteamID must be a number with no spaces. To learn how to find your SteamID, type the **/help** command."
            elif steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'DiscordUserName': username,
                    'DiscordGlobalName': globalname,
                    'lastUpdated': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # Format timestamp as desired
                }
                table.put_item(Item=item)
                result_string=f"Killer stats for Steam Username **{steamusername}** requested by **@{username}** *(User ID: {steamuserid})*: \n"
                thissurvivorstat=[]
                for stat in killercharacterstats:
                    teststatresult = get_dbd_player_stats(steamapikey, steamuserid, stat)
                    thissurvivorstat
                    this_message = f"{descriptors[stat]}: **{teststatresult}** \n"
                    result_string += this_message
                    print(f"Log from local desktop - stat is {stat}, message_content is:")
                    print(this_message)
                message_content = result_string
        elif command_name == "stats":
            steamuserid = data["options"][0]["value"]
            message_sender = data["id"]
            spacecheck = bool(re.search(r"\s", steamuserid))
            if spacecheck==True:
                message_content = "SteamID must be a number with no spaces. To learn how to find your SteamID, type the **/help** command."
            elif steamuserid.isnumeric():
                steamusername=get_steam_username(steamapikey, steamuserid)
                item = {
                    'SteamUserID': int(steamuserid),
                    'SteamUserName': steamusername,
                    'DiscordUserID': message_sender,
                    'DiscordUserName': username,
                    'DiscordGlobalName': globalname,
                    'lastUpdated': datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')  # Format timestamp as desired
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
        elif command_name == "shrine":
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
                #print(this_shrine_perk.name)
                #print(this_shrine_perk.description)
                #print(this_shrine_perk.bloodpointcost)
                #print(this_shrine_perk.shardcost)
                result_string+=f"**{this_shrine_perk.name}** \n Bloodpoint cost: **{this_shrine_perk.bloodpointcost}** \n Shard cost: **{this_shrine_perk.shardcost}** \n Perk ID: **{thisperk}** *Perk ID can be used to look up the perk's description using the **/perk {thisperk}** command* \n"
            print(f"Log from main.py - Discord user {username} requested current shrine perks. message_content: ")
            print(result_string)
            message_content = result_string
        elif command_name == "perk":
            perk = data["options"][0]["value"]
            message_sender = data["id"]
            perkurl="https://dbd.tricky.lol/api/perkinfo"
            thisperkurl=f"{perkurl}?perk={perk}"
            try:
                perkresponse=requests.get(thisperkurl)
                thisperkinfo = perkresponse.json()
                perk_name = thisperkinfo["name"]
                replaced_description=replace_numbers_in_description(thisperkinfo)
                new_description=replace_html_tags(replaced_description["description"])
                message_content=f"**Name:** {perk_name} \n**ID:** {perk}\n**Description:** {new_description}"
            except:
                message_content=f"Failed to get Perk information for: {perk}"

        # Form the message to be sent to Discord
        response_data = {
            "type": 4,
            "data": {"content": message_content},
        }

    return jsonify(response_data)

# For testing the app locally (run main.py and copy a Discord request from the Cloudwatch logs)
if __name__ == "__main__":
    app.run(debug=True)
