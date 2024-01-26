import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as path from 'path';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as events from 'aws-cdk-lib/aws-events';

const config = require('../config.json');
const discordPublicKey = config.DISCORD_PUBLIC_KEY;
const steamapikey = config.steamapikey;
const discord_bot_token = config.DISCORD_BOT_TOKEN;
const channel_id= config.channel_id;

export class DiscordBotLambdaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define the Dynamo DB Tables
    const userCacheTable = new dynamodb.Table(this, 'SteamIDCache', {
      partitionKey: { name: 'SteamUserID', type: dynamodb.AttributeType.NUMBER },
      tableName: 'SteamIDCache',
      sortKey: { name: 'lastUpdated', type: dynamodb.AttributeType.STRING },
      removalPolicy: cdk.RemovalPolicy.RETAIN, // WARNING: This will delete the table and all data when the stack is deleted
    });
    userCacheTable.addGlobalSecondaryIndex({
      indexName: 'SteamUserNameIndex',
      partitionKey: {
        name: 'SteamUserName',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    const userStatTable = new dynamodb.Table(this, 'userStatCache', {
      partitionKey: { name: 'SteamUserID', type: dynamodb.AttributeType.NUMBER },
      sortKey: { name: 'date', type: dynamodb.AttributeType.STRING },
      tableName: 'userStatCache',
      removalPolicy: cdk.RemovalPolicy.RETAIN, // WARNING: This will delete the table and all data when the stack is deleted
    });
    userStatTable.addGlobalSecondaryIndex({
      indexName:'date-index',
      partitionKey: {
        name: 'date',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    const perkTable = new dynamodb.Table(this, 'perkTable', {
      partitionKey: { name: 'perk_id', type: dynamodb.AttributeType.STRING },
      tableName: 'dbdPerkCache',
      sortKey: { name: 'name', type: dynamodb.AttributeType.STRING },
      removalPolicy: cdk.RemovalPolicy.RETAIN, // WARNING: This will delete the table and all data when the stack is deleted
    });
    perkTable.addGlobalSecondaryIndex({
      indexName: 'PerkNameIndex',
      partitionKey: {
        name: 'name',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    const awardTable = new dynamodb.Table(this, 'awardTable', {
      partitionKey: { name: 'SteamUserID', type: dynamodb.AttributeType.NUMBER },
      tableName: 'awardTable',
      sortKey: { name: 'date', type: dynamodb.AttributeType.STRING },
      removalPolicy: cdk.RemovalPolicy.RETAIN, // WARNING: This will delete the table and all data when the stack is deleted
    });
    perkTable.addGlobalSecondaryIndex({
      indexName: 'AwardNameIndex',
      partitionKey: {
        name: 'awards',
        type: dynamodb.AttributeType.STRING,
      },
      projectionType: dynamodb.ProjectionType.ALL,
    });

    // Define the main.py Lambda Function
    const dockerFunction = new lambda.DockerImageFunction(
      this,
      "DockerFunction",
      {
        code: lambda.DockerImageCode.fromImageAsset("./src/"),
        memorySize: 1024,
        timeout: cdk.Duration.seconds(15),
        architecture: lambda.Architecture.X86_64,
        environment: {
          DISCORD_PUBLIC_KEY: discordPublicKey,
          USER_CACHE_TABLE: userCacheTable.tableName,
          PERK_CACHE_TABLE: perkTable.tableName,
          steamapikey: steamapikey,
          award_table_name: awardTable.tableName
        },
      }
    );
    userStatTable.grantReadWriteData(dockerFunction);
    awardTable.grantReadWriteData(dockerFunction);
    perkTable.grantReadData(dockerFunction);
    userCacheTable.grantReadWriteData(dockerFunction);

    // Define the Docker Function URL
    const functionUrl = dockerFunction.addFunctionUrl({
      authType: lambda.FunctionUrlAuthType.NONE,
      cors: {
        allowedOrigins: ["*"],
        allowedMethods: [lambda.HttpMethod.ALL],
        allowedHeaders: ["*"],
      },
    });

    // Define the Stat Table Updater Lambda
    const statTableUpdater = new lambda.DockerImageFunction(this, 'StatTableUpdaterv2', {
      code: lambda.DockerImageCode.fromImageAsset("./scripts/stat_table_update/"),
      memorySize: 256,
      timeout: cdk.Duration.seconds(20),
      architecture: lambda.Architecture.X86_64,
      environment: {
        DISCORD_PUBLIC_KEY: discordPublicKey,
        USER_STAT_TABLE: userStatTable.tableName,
        USER_CACHE_TABLE: userCacheTable.tableName,
        steamapikey: steamapikey
      },
    });
    userCacheTable.grantReadWriteData(statTableUpdater);
    userStatTable.grantReadWriteData(statTableUpdater);

    // Define the Perk Cache Updater Lambda
    const perkCacheUpdater = new lambda.DockerImageFunction(this, 'perkCacheUpdaterv2', {
      code: lambda.DockerImageCode.fromImageAsset("./scripts/perk_cache_update/"),
      memorySize: 256,
      timeout: cdk.Duration.seconds(60),
      architecture: lambda.Architecture.X86_64,
      environment: {
        DYNAMODB_TABLE_NAME: perkTable.tableName,
      },
    });

    perkTable.grantReadWriteData(perkCacheUpdater);

    const userCacheUpdater = new lambda.DockerImageFunction(this, 'userCacheUpdater', {
      code: lambda.DockerImageCode.fromImageAsset("./scripts/user_cache_updater/"),
      memorySize: 256,
      timeout: cdk.Duration.seconds(10),
      architecture: lambda.Architecture.X86_64,
      environment: {
        USER_CACHE_TABLE: userCacheTable.tableName,
        steamapikey: steamapikey
      },
    });
    userCacheTable.grantReadWriteData(userCacheUpdater);

    const awardUpdater = new lambda.DockerImageFunction(this, 'awardUpdater', {
      code: lambda.DockerImageCode.fromImageAsset("./scripts/award_updater/"),
      memorySize: 256,
      timeout: cdk.Duration.seconds(90),
      architecture: lambda.Architecture.X86_64,
      environment: {
        DISCORD_PUBLIC_KEY: discordPublicKey,
        USER_STAT_TABLE: userStatTable.tableName,
        USER_CACHE_TABLE: userCacheTable.tableName,
        award_table_name: awardTable.tableName,
        steam_api_key: steamapikey,
        DISCORD_BOT_TOKEN: discord_bot_token,
        channel_id: channel_id
        
      },
    });
    userCacheTable.grantReadWriteData(awardUpdater);
    userStatTable.grantReadWriteData(awardUpdater);
    awardTable.grantReadWriteData(awardUpdater)

    // CloudWatch Event Rules
    const statTableEventRule = new events.Rule(this, 'statTableEventRule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '10', weekDay: 'SUN-SAT' }), // Trigger every day at 2:00 AM Pacific Time
    });

    statTableEventRule.addTarget(new targets.LambdaFunction(statTableUpdater));

    const perkCacheEventRule = new events.Rule(this, 'perkCacheEventRule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '12', weekDay: 'SUN-SAT' }), // Trigger every day at 4:00 AM Pacific Time
    });
  
    perkCacheEventRule.addTarget(new targets.LambdaFunction(perkCacheUpdater));

    const userCacheEventRule = new events.Rule(this, 'userCacheEventRule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '*' }), // Trigger every hour
    });
    userCacheEventRule.addTarget(new targets.LambdaFunction(userCacheUpdater));

    const awardUpdaterEventRule = new events.Rule(this, 'awardsEventRule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '4', weekDay: 'SUN' }), // Trigger every hour
    })
    awardUpdaterEventRule.addTarget(new targets.LambdaFunction(awardUpdater));

    new cdk.CfnOutput(this, "FunctionUrl", {
      value: functionUrl.url,
    });
  }
}
