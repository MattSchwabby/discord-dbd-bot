# DBD-Discord-Bot

This repo contains a Discord bot written in Python that gets user stats and other information for the game Dead by Daylight from the [Steam API](https://steamcommunity.com/dev) and the [DBD Playerstats API](https://dbd.tricky.lol/).

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
```
Steam requires a users SteamID to look up their player stats. No one can look up someone else's SteamID, so these commands only work if a user provides a SteamID with the request. Your SteamID is a unique identifier that's 17 numbers long and different than your username. To look up your SteamID, open Steam, click your username in the upper right hand side of the application, select `Account Details``. Your Steam ID is below your username.

Also, your Steam Profile & Game details must be set to public to get your information from the Steam API. To set your profile to public, open your profile in Steam and click `Edit Profile`, then set `My profile` and `Game details` to Public ([Click here for examples of how to look up your SteamID and set your profile to public](https://imgur.com/a/Xw3KbJ5))."

Example of the /stats command:
![/stats](https://i.imgur.com/lUi2DwE.png)

Example of the /shrine command:
![/shrine](https://i.imgur.com/VhQkOWN.png)

#### Functionality In Development

You'll notice that the CDK app deploys some DynamoDB tables, cloudwatch event bridge rules, and two Lambda functions that don't appear to be related to the Discord functionality. This is for two reasons:
1 - I'm working on an update to the /perk command which will allow users to search for perks using their name instead of their PerkID.
2 - I'm working on functionality that will track the stats of each user that has interacted with the bot over time. I plan on building leaderboard-style functionality where the bot will post in a channel about who gained the most points in a particular stat or stats each week.

#### Using the Bot

You can add the current version of the bot to your Discord server by [clicking this link](https://discord.com/api/oauth2/authorize?client_id=1065388537949720596&permissions=1085016635456&scope=bot) and then choosing your desired server in the drop down list.

![Adding the bot](https://i.imgur.com/NuevfNC.png)

### Discord

This bot uses the [Discord Interactions Endpoint](https://discord.com/developers/docs/interactions/application-commands). All interactions with the bot require a user to interact with the bot first. This bot cannot do anything without a user first interacting with it.

### Modifying the Bot

To modify this bot, you'll need a [Steam API key](https://steamcommunity.com/dev), your own [Discord Application](https://discord.com/developers/applications), and [an AWS account](https://aws.amazon.com).

Once you have all those, you'll need to clone this repo and create a file named `config.json` in the root of the project and populate it with a couple of configuration values:
```
{
    "DISCORD_PUBLIC_KEY": "DISCORD PUBLIC KEY GOES HERE", # This is the public key of your Discord application
    "steamapikey": "YOUR STEAM API KEY GOES HERE" # Your Steam API key
}
```
### Registering the Commands with Discord

Next, you'll need to register your custom commands with Discord.

Modify the `discord_commands.yaml` file to add your desired commands. Also install the dependencies in `requirements.txt` locally if you haven't already.

```sh
pip install -r commands/requirements.txt
```

Then create a file named `discordsecrets.py` in the same directory as `register_commands.py` and populate it with the API key and application ID for your Discord bot:
```
TOKEN = "DISCORD APPLICATION TOKEN" # Your Discord Application token goes here
APPLICATION_ID = "DISCORD APPLICATION ID" # Your Discord Application ID goes here

```
After that, run  `register_commands.py` from the `commands` directory to register your commands with Discord.

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

### Deploying to AWS Lambda

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