# DBD-Discord-Bot

This repo contains a Discord bot written in Python that gets user stats and other information for the game Dead by Daylight from the [Steam API](https://steamcommunity.com/dev) and the [DBD Playerstats API](https://dbd.tricky.lol/), tracks the stats of users that have interacted with the bot in AWS, and operates a weekly leaderboard based on those stats.

It is based on [`discord-bot-lambda`](https://github.com/pixegami/discord-bot-lambda) created by [Pixegami](https://github.com/pixegami/) on Github.

### Functionality

The bot's commands are outlined in the `discord_commands.yaml` file in the `/commands/` folder. The current functions are:

```
/help - Returns information about how to use the bot.
/shrine - Looks up the current perks in the Shrine of Secrets and their cost. Usage: /shrine.
/perk - Looks up the description for a given perk ID. Meant to be used after getting a Perk ID from /shrine. Usage: /perk <Perk ID>.
/stats - Looks up overall Dead by Daylight stastics, like number of matches escaped as a survivor and number of survivors sacrificed as killer. Usage: /stats <SteamID>.
/survivorstats - Looks up Dead By Daylight survivor statistics, ex.: # of games escaped, # of generators repaire. Usage: /survivorstats <SteamID> .
/survivormapstats - Looks up map-specific survivor statistics. Usage: /survivormapstats <SteamID>.
/killerstats - Looks up Dead by Daylight Killer statistics, like: # of survivors hooked, # of survivors killed. Usage: /killerstats <SteamID>.
/killercharacterstats - Looks up character-specific stats as kille. Usage: /killercharacterstats <SteamID>
/users - Gets the current list of cached usernames. Cache updates every hour.
/leaderboard - Gets the current awards for each person in the user cache.
/awards - Lists available rewards and descriptions.
```
Steam requires a users SteamID to look up their player stats. No one can look up someone else's SteamID, so these commands only work if a user provides a SteamID with the request. If you've used the bit with a SteamID at least once, it will cache your Steam username and you can use that instead of your SteamID in subsequent commands.

Your SteamID is a unique identifier that's 17 numbers long and different than your username. To look up your SteamID, open Steam, click your username in the upper right hand side of the application, select `Account Details``. Your Steam ID is below your username.

Also, your Steam Profile & Game details must be set to public to get your information from the Steam API. To set your profile to public, open your profile in Steam and click `Edit Profile`, then set `My profile` and `Game details` to Public ([Click here for examples of how to look up your SteamID and set your profile to public](https://imgur.com/a/Xw3KbJ5))."

Example of the /stats command:
![/stats](https://i.imgur.com/lUi2DwE.png)

Example of the weekly leaderboard:
![leaderboard](https://imgur.com/NHY8cRR)

Example of the /shrine command:
![/shrine](https://i.imgur.com/VhQkOWN.png)

Example of the /leaderboard command:
![/leaderboard](https://imgur.com/r31tkUO)

Example of the /perk comannd:
~[/perk](https://imgur.com/ocOA2LD)

#### Leaderboards

After a member of the Discord server has interacted with the bot using their SteamID at least once, the bot will start tracking that user's stats for the weekly leaderboard. Every Saturday at 8 PM Pacific, the bot will post the winners of various awards in a configured channel. The awards that are currently available are:

```
🥈: Runner up
🚑: Most survivors recovered from dying
🧙‍♀️: Most hex totems cleansed
🔒: Most vaults while in a chase
🐌: Most escapes while crawling (downed)
🐀: Most crawling (downed) hatch escapes
🕳️: Most escapes through the hatch
🥤:potato:: Most perfect games: 5k+ in all categories)
🛡️: Most protection hits for a survivor that was just unhooked
👻: Most season ranks
:hook:: Most self-unhooks
🤬: Most vaults that made a killer miss an attack
✅: Most successful skill checks
☕: Repairing the chalet generator and escaping from Ormond
🩹: Most survivors healed
⚰️: Most escapes after getting downed at least once
🔧: Repairing the most generators
🩸: Most Bloodpoints
👟: Total Wins
⛩️: Most exit gates opened
```

### Using this bot

To use this bot, you'll need a Discord application, an AWS account, and a Discord server where you have administrator privileges and can add bots to the server, and add bots to channels on that server. After copying this codebase and modifying some configuration values, all you need to do is deploy the code to your AWS account, then add the bot to your server. The leaderboard functionality is optional - if you want to use it, then add the bot to the channel you'd like them to post the weekly leaderboard results in.

#### Discord

This bot uses the [Discord Interactions Endpoint](https://discord.com/developers/docs/interactions/application-commands). All of the slash commands (such as /shrine) require a user to first interact with the bot. The only functionality that happens automatically is the user cache update, and the weekly leaderboard post.

#### Setting up the Bot

To set up this bot in your own Discord server, you'll need a [Steam API key](https://steamcommunity.com/dev), your own [Discord Application](https://discord.com/developers/applications), and [an AWS account](https://aws.amazon.com).

Once you have all those, you'll need to clone this repo and create a file named `config.json` in the root of the project, and populate it with a couple of configuration values:
```
{
    "DISCORD_PUBLIC_KEY": "DISCORD PUBLIC KEY GOES HERE", # This is the public key of your Discord application
    "steamapikey": "YOUR STEAM API KEY GOES HERE" # Your Steam API key,
    "DISCORD_BOT_TOKEN": "DISCORD BOT TOKEN GOES HERE" # Your discord bot token
    "channel_id":"DISCORD CHANNEL ID GOES HERE" # The channel ID of the channel you'd like the bot to post leaderboards in (optional - you don't need to configure this if you don't want to use the leaderboard functionality).
}

```
#### Registering the Commands with Discord

Next, you'll need to register your custom commands with Discord.

Modify the `discord_commands.yaml` file to add your desired commands, or use the ones I've already configured. Also install the dependencies in `requirements.txt` locally if you haven't already.

```sh
pip install -r commands/requirements.txt
```

After that, create a file named `discordsecrets.py` in the same directory as `register_commands.py` and populate it with the API key and application ID for your Discord bot:

```
TOKEN = "DISCORD APPLICATION TOKEN" # Your Discord Application token goes here
APPLICATION_ID = "DISCORD APPLICATION ID" # Your Discord Application ID goes here

```
Then, run  `register_commands.py` from the `commands` directory to register your commands with Discord.

```sh
cd commands
python register_commands.py
```

### Application  Information

The app is built with [Flask](https://flask.palletsprojects.com/) to create a HTTP server.
The server is hosted on AWS Lambda Docker Container using [AWS CDK](https://aws.amazon.com/cdk/).

#### Testing Locally

To test the server locally, put a sample request (which you can get by logging the JSON in Lambda) in the `test_request.json` file.

Start up the bot as a Flask app.

```sh
python src/app/main.py
```

Then send the request to the Flask app.

```sh
curl -X POST -H "Content-Type: application/json" -d @test_request.json http://127.0.0.1:5000/
```

But this won't work with the `@verify_key_decorator`, because the request won't have a token that works with the public key.

So you'll need to comment out the decorator to test locally or update the example request with a valid token from your Lambda logs.

### Deploying to AWS

After copying this code and setting your configuration values, you'll need to deploy this bot to AWS. Since it's a CDK application you can do this with just a couple of commands.

####

 Bootstrap the CDK if you haven't already.

```sh
cdk bootstrap
```

Then you can run this to deploy it (make sure your AWS CLI is set up first).

```sh
cdk deploy
```

Enjoy!

If you'd like to make a Discord bot for other purposes, I recommend you check out [Pixegami's original repo](https://github.com/pixegami/discord-bot-lambda).