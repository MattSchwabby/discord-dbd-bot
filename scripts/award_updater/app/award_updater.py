import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Key
import json
from collections import defaultdict
from datetime import datetime, timedelta
import requests
import discord
from discord.ext import commands
import os
import calendar
import csv
from decimal import Decimal

survivor_stats={
    "DBD_Chapter9_Camper_Stat1",
    'DBD_EscapeKO',
    'DBD_CamperSkulls',
    'DBD_GeneratorPct_float',
    "DBD_DLC7_Camper_Stat2",
    "DBD_Chapter15_Camper_Stat1",
    "DBD_Camper8_Stat2",
    "DBD_DLC9_Camper_Stat1",
    "DBD_Chapter12_Camper_Stat2",
    "DBD_DLC3_Camper_Stat1",
    "DBD_HitNearHook",
    'DBD_HealPct_float',
    "DBD_SkillCheckSuccess",
    "DBD_CamperMaxScoreByCategory",
    "DBD_DLC8_Camper_Stat1",
    'DBD_EscapeThroughHatch',
    "DBD_BloodwebPoints"
}

descriptors={
    "total_wins":"👟 The Escapee award for most escapes",
    "DBD_BloodwebPoints":"🩸 The Blood Boy award for gaining the most Bloodpoints",
    "DBD_CamperMaxScoreByCategory":"🥤:potato: The Mountain Dew and Doritos Leet Gamer award (most perfect games: 5k+ in all categories)",
    'DBD_CamperSkulls':"👻 The Spooky Boy award for gaining the most season ranks",
    'DBD_GeneratorPct_float':"🔧 The Handyman award for repairing the most generators",
    "DBD_Chapter12_Camper_Stat2":"🐀 The Sewer Rat award for most times you escaped by crawling in the hatch (downed)",
    "DBD_Chapter9_Camper_Stat1":":hook: The Deliverance award for the most times you unhooked yourself",
    'DBD_EscapeKO':"🐌 The Slippery Slug award for the most times you escaped while crawling (downed)",
    'DBD_HealPct_float':"🩹 The Bruce Cusamano award for most survivors healed",
    "DBD_SkillCheckSuccess":"✅ The Completionist award for most successful skill checks",
    "DBD_DLC9_Camper_Stat1":"🤬 The Lithe award for the most vaults that made a killer miss an attack",
    "DBD_Camper8_Stat2":"🔒 The Fort Knox award for most vaults while in a chase",
    "DBD_DLC7_Camper_Stat2":"⛩️ The Torii award for opening the most exit gates",
    "DBD_Chapter15_Camper_Stat1":"🚑 The Amber Lamps award for recovering the most survivors from dying",
    "DBD_DLC3_Camper_Stat1":"🧙‍♀️ The Witchhunter award for most hex totems cleansed",
    "DBD_HitNearHook":"🛡️ The Lord Protector award for most protection hits for a survivor that was just unhooked",
    'DBD_EscapeThroughHatch':"🕳️ The Lube Man award for most escapes through the hatch",
    "DBD_DLC8_Camper_Stat1":"⚰️ The Undertaker award for escapes after getting downed at least once",
    "DBD_FixSecondFloorGenerator_MapKny_Cottage":"☕ The Cozy Boy award for repairing the chalet generator and escaping from Ormond"
}

def get_current_date():
    # Get the current date in the format 'YYYY-MM-DD'
    return datetime.now().strftime('%Y-%m-%d')

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

def get_current_date():
    # Get the current date in the format 'YYYY-MM-DD'
    return datetime.now().strftime('%Y-%m-%d')

def get_latest_steam_userid_dynamo(table_name,steam_user_name):
    dynamodb = boto3.resource('dynamodb')
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

def update_award_value(data, award_names):
    # Ensure 'awards' key is present in data
    if 'awards' not in data[0]:
        data[0]['awards'] = {'awards': []}

    # Iterate through the award_names and update/increment the specified award
    for award_name in award_names:
        award_found = False
        for award in data[0]['awards']:
            if award['name'] == award_name:
                award['value'] += Decimal('1')
                award_found = True
                break

        # If the award is not found, add it to the awards list with a value of 1
        if not award_found:
            new_award = {'name': award_name, 'value': Decimal('1')}
            data[0]['awards'].append(new_award)

    return data

def put_awards(award_table_name,steam_user_id,awards,week_and_year):
    dynamodb = boto3.resource('dynamodb')
    award_table = dynamodb.Table(award_table_name)
    today = datetime.now()
    # Get current ISO 8601 datetime in string format
    iso_date = today.isoformat()
    current_awards=get_awards(award_table_name,steam_user_id)
    if current_awards[0]["last_awarded"]==week_and_year:
        message=f"We already have awards for {week_and_year}"
        return message
    item={
        'SteamUserID':Decimal(steam_user_id),
        'date': iso_date,
        "last_awarded": week_and_year,
        'awards': awards[0]['awards']
    }
    award_table.put_item(Item=item)
    message=f"wrote {awards} to awards DB"
    return message


def get_awards(award_table_name,steam_user_id):
    dynamodb = boto3.resource('dynamodb')
    award_table = dynamodb.Table(award_table_name)
    key_condition_expression = Key('SteamUserID').eq(steam_user_id)
    response = award_table.query(
        KeyConditionExpression=key_condition_expression,
        ScanIndexForward=False,
        Limit=1  # Limit the result to only one item
    )
    if response['Items']:
        return response['Items']
    else:
        current_date = get_current_date()
        week_number = datetime.strptime(current_date, '%Y-%m-%d').isocalendar()[1]
        current_year = datetime.now().year 
        week_and_year=f"{current_year}-{week_number}"
        today = datetime.now()
        # Get current ISO 8601 datetime in string format
        iso_date = today.isoformat()
        item = [{
            'SteamUserID': int(steam_user_id),
            'awards':[],
            'last_awarded':""
            }]
        
        return item

def steam_id_exists_in_dynamo_results(steam_id, data):
    return any(user['SteamID'] == steam_id for user in data)

def add_new_steam_user_dynamo_results(steam_id, data):
    data.append({
        'SteamID': steam_id,
        'Awards': []
    })
    return data

def add_award_to_steam_user_dynamo_results(steam_id, award, data):
    for user in data:
        if user['SteamID'] == steam_id:
            user['Awards'].append(award)
            break
    return data



def handler(event, context):
    # Initialize DynamoDB client
    dynamodb = boto3.resource('dynamodb')
    user_table_name = os.environ['USER_CACHE_TABLE']
    stat_table_name = os.environ['USER_STAT_TABLE']
    user_table = dynamodb.Table(user_table_name)
    stat_table = dynamodb.Table(stat_table_name)
    api_key = os.environ['steam_api_key']
    channel_id=os.environ['channel_id']
    award_table_name = os.environ['AWARD_TABLE']
    award_table = dynamodb.Table(award_table_name)
    bot_token=os.environ['DISCORD_BOT_TOKEN']
    current_date = get_current_date()
    week_number = datetime.strptime(current_date, '%Y-%m-%d').isocalendar()[1]
    current_year = datetime.now().year 
    week_and_year=f"{current_year}-{week_number}"
    # Query DynamoDB table for all SteamUserIDs
    response = user_table.scan()

    # Create a dictionary to store the most recent item for each SteamUserID
    latest_items = defaultdict(dict)

    # Iterate through items in the response
    for item in response['Items']:
        steam_user_id = item['SteamUserID']
        last_updated = item['lastUpdated']
        steam_user_name = item['SteamUserName']

        # Check if the current item is more recent than the stored item for the SteamUserID
        if last_updated > latest_items[steam_user_id].get('lastUpdated', '0'):
            latest_items[steam_user_id] = item

    # Print or further process the latest items
    '''
    for steam_user_id, item in latest_items.items():
        print(f"SteamUserID: {steam_user_id}, SteamUserName: {item['SteamUserName']}")

    '''
    one_week_ago = (datetime.now() - timedelta(days=7)).isoformat()
    index_name = 'date-index'
    spooky_stats = []
    for steam_user_id, item in latest_items.items():
        recent_response = stat_table.query(
            KeyConditionExpression="#uid = :uid",
            ExpressionAttributeNames={
                "#uid": "SteamUserID"
            },
            ExpressionAttributeValues={
                ":uid": steam_user_id
            },
            ScanIndexForward=False,  # Sort in descending order by default
            Limit=1  # Limit to only retrieve the latest item
        )
        recent_items = recent_response.get('Items', [])
        
        if recent_items:
            latest_item = recent_items[0]
            stats = json.loads(latest_item['stats'])
            PROCESS_USER=True
            #print(f"Latest item for SteamUserID {steam_user_id}:")
        else:
            PROCESS_USER=False;
            message=f"No items found for SteamUserID {steam_user_id}"
            print(message)

        if PROCESS_USER==True:
            last_week_response = stat_table.query(
                #IndexName=index_name, 
                KeyConditionExpression="#uid = :uid AND #date <= :one_week_ago",
                ExpressionAttributeNames={
                    "#uid": "SteamUserID",
                    "#date": "date"
                },
                ExpressionAttributeValues={
                    ":uid": steam_user_id,
                    ":one_week_ago": one_week_ago
                },
                ScanIndexForward=False,  # Sort in descending order by default
                Limit=1
            )

            old_items = last_week_response.get('Items', [])
            
            if old_items:
                oldest_item = old_items[0]
                old_stats = json.loads(oldest_item['stats'])
            for stat in stats:
                #print(f"Stat: {stat['name']}")
                target_name=stat['name']
                if target_name in survivor_stats:
                    latest_value = next((entry for entry in stats if entry['name'] == target_name), None)
                    last_week_value = next((entry for entry in old_stats if entry['name'] == target_name), None)
                    difference = latest_value['value'] - last_week_value['value']
                    spooky_stat ={
                        "SteamUserId": steam_user_id,
                        "stat_name": stat['name'],
                        "difference": difference
                    }
                    spooky_stats.append(spooky_stat)
    winners=[]
    second_placers=[]
    third_placers=[]

    text_file_name = "survivor_stats.txt"
    with open(text_file_name, 'w') as file:
        for element in spooky_stats:
            file.write(str(element) + '\n')

    message_content="👻👻👻 THIS WEEK'S SPOOKY AWARDS 👻👻👻\n\n"
    for survivor_stat in survivor_stats:
        filtered_data = [stat for stat in spooky_stats if stat["stat_name"]==survivor_stat]
        max_stat = max(filtered_data, key=lambda ev: ev['difference'])
        if(max_stat['difference'] > 0):
            winners.append(max_stat)
        losers = filtered_data
        filtered_data.remove(max_stat)
        #print(losers)
        second_place = max(losers, key=lambda ev: ev['difference'])
        losers.remove(second_place)
        third_place = max(losers, key=lambda ev: ev['difference'])
        if(second_place['difference'] > 0):
            second_placers.append(second_place)
        if(third_place['difference'] > 0):
            third_placers.append(third_place)

    dynamo_results = []
    for winner in winners:
        stat = winner['stat_name']
        winner_steam_id = winner['SteamUserId']
        winning_difference=round(winner['difference'])
        this_description = descriptors[stat]
        winner_steam_user_name=get_steam_username(api_key, winner_steam_id)
        runner_up=[item for item in second_placers if item["stat_name"]==stat]

        # Add the winner's Steam ID to the dynamo results
        winner_steam_id_dynamo={'SteamID': winner_steam_id}
        if not steam_id_exists_in_dynamo_results(winner_steam_id_dynamo['SteamID'],dynamo_results):
            dynamo_results = add_new_steam_user_dynamo_results(winner_steam_id_dynamo['SteamID'],dynamo_results)
        if(runner_up):
            runner_up_steam_id=int(runner_up[0]['SteamUserId'])
            # Add the runner up's Steam ID to the dynamo results
            runner_up_id_dynamo={'SteamID': runner_up_steam_id}
            if not steam_id_exists_in_dynamo_results(runner_up_id_dynamo['SteamID'],dynamo_results):
                dynamo_results = add_new_steam_user_dynamo_results(runner_up_id_dynamo['SteamID'],dynamo_results)
            second_place=get_steam_username(api_key, runner_up_steam_id)
            second_place_score=round(runner_up[0]['difference'])
            third_runner_up = [item for item in third_placers if item["stat_name"]==stat]
            if(third_runner_up):
                third_place_score=round(third_runner_up[0]['difference'])
                third_place_steamid=third_runner_up[0]['SteamUserId']
                # Add the third runner up's Steam ID to the dynamo results
                third_runner_up_id_dynamo={'SteamID': third_place_steamid}
                if not steam_id_exists_in_dynamo_results(runner_up_id_dynamo['SteamID'],dynamo_results):
                    dynamo_results = add_new_steam_user_dynamo_results(runner_up_id_dynamo['SteamID'],dynamo_results)
                third_place_steam_name=get_steam_username(api_key, third_place_steamid)
            if third_place_score in locals() and winning_difference==third_place_score:
                message_content+=f"{this_description} is a THREE WAY TIE! **{winner_steam_user_name}** and **{second_place}** and **{third_place_steam_name}** tie with **{winning_difference}**\n"
                # Add award for the winner to the Dynamo Result
                add_award_to_steam_user_dynamo_results(winner_steam_id,stat,dynamo_results)
                # Add award for tie 1
                add_award_to_steam_user_dynamo_results(runner_up_steam_id,stat,dynamo_results)
                # Add award for tie 2
                add_award_to_steam_user_dynamo_results(third_place_steamid,stat,dynamo_results)
            elif(winning_difference==second_place_score):
                #print(f"Found a tie - winning_difference is {winning_difference}, second_place_score is {second_place_score}")
                message_content+=f"{this_description} is a TIE! **{winner_steam_user_name}** and **{second_place}** tie with **{winning_difference}** | Runner up was **{third_place_steam_name}** with **{third_place_score}**\n"
                # Add award for the winner to the Dynamo Result
                add_award_to_steam_user_dynamo_results(winner_steam_id,stat,dynamo_results)
                # Add award for tie 1
                add_award_to_steam_user_dynamo_results(runner_up_steam_id,stat,dynamo_results)
                # Add runner up award
                add_award_to_steam_user_dynamo_results(third_place_steamid,"runner_up",dynamo_results)
                #print(f"{winner_steam_id},{stat}")
            else:
                message_content+=f"{this_description} goes to **{winner_steam_user_name}** with **{winning_difference}** | Runner up was **{second_place}** with **{second_place_score}**\n"
                # Add award for the winner to the Dynamo Result
                add_award_to_steam_user_dynamo_results(winner_steam_id,stat,dynamo_results)
                add_award_to_steam_user_dynamo_results(runner_up_steam_id,"runner_up",dynamo_results)
        else:
            message_content+=f"{this_description} goes to **{winner_steam_user_name}** with **{winning_difference}**\n"
            # Add award for the winner to the Dynamo Result
            add_award_to_steam_user_dynamo_results(winner_steam_id,stat,dynamo_results)

            #add_award(winner_steam_id, stat, AWARD_TABLE)


    for result in dynamo_results:
        steam_user_id=result['SteamID']
        awards=result['Awards']
        current_awards=get_awards(award_table_name,steam_user_id)
        updated_awards = update_award_value(current_awards,awards)
        put_awards(award_table_name,steam_user_id,updated_awards,week_and_year)

    message_length=len(message_content)
    newline_count=message_content.count('\n')

    intents = discord.Intents.default()
    intents.messages = True

    bot = commands.Bot(command_prefix='!', intents=intents)

    @bot.event
    async def on_ready():
        print(f'Logged in as {bot.user.name} ({bot.user.id})')
        print('------')
        channel = bot.get_channel(channel_id)

        if channel:
            print("trying to send message:")
            print(message_content)
            print(f"message length is {len(message_content)}, there are {newline_count} line breaks")
            if(message_length > 1900):
                split_index = (newline_count + 1) // 2  # Adding 1 to get the middle index
                print(f"message length is over 1900, splitting into two messages:")
                print(f"split_index is {split_index}")

                lines = message_content.split('\n')
                first_part = '\n'.join(lines[:split_index])
                second_part = '\n'.join(lines[split_index:])
                await channel.send(first_part)
                await channel.send(second_part)
            else:
                await channel.send(message_content)

            await bot.close()
        else:
            print(f"Channel with ID {channel_id} not found.")
            await bot.close()

    # Run the bot with your token
    bot.run(bot_token)
    return "Executed bot script for awards"

    '''
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
        if(perk_name=="Repressed Alliance"):
            perk_name="Repressed&nbsp;Alliance"
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
            perk_id = dynamo_response.get('perk_id')'''