import * as cdk from "aws-cdk-lib";
import { Construct } from "constructs";
import * as lambda from "aws-cdk-lib/aws-lambda";
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as path from 'path';
import * as targets from 'aws-cdk-lib/aws-events-targets';
import * as events from 'aws-cdk-lib/aws-events';

const config = require('../config.json');
const discordPublicKey = config.DISCORD_PUBLIC_KEY;
const steamapikey = config.steamapikey

export class DiscordBotLambdaStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Define the Dynamo DB Tables
    const userCacheTable = new dynamodb.Table(this, 'SteamIDCache', {
      partitionKey: { name: 'SteamUserID', type: dynamodb.AttributeType.NUMBER },
      tableName: 'SteamIDCache',
      sortKey: { name: 'date', type: dynamodb.AttributeType.STRING },
      removalPolicy: cdk.RemovalPolicy.DESTROY, // WARNING: This will delete the table and all data when the stack is deleted
    });

    const userStatTable = new dynamodb.Table(this, 'userStatCache', {
      partitionKey: { name: 'SteamUserID', type: dynamodb.AttributeType.NUMBER },
      sortKey: { name: 'date', type: dynamodb.AttributeType.STRING },
      tableName: 'userStatCache',
      removalPolicy: cdk.RemovalPolicy.DESTROY, // WARNING: This will delete the table and all data when the stack is deleted
    });

    const perkTable = new dynamodb.Table(this, 'perkTable', {
      partitionKey: { name: 'perk_id', type: dynamodb.AttributeType.STRING },
      tableName: 'dbdPerkCache',
      removalPolicy: cdk.RemovalPolicy.DESTROY, // WARNING: This will delete the table and all data when the stack is deleted
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
          steamapikey: steamapikey
        },
      }
    );

    userCacheTable.grantWriteData(dockerFunction);

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
    const statTableUpdater = new lambda.Function(this, 'StatTableUpdater', {
      runtime: lambda.Runtime.PYTHON_3_8,
      handler: 'stat_table_update.handler',
      code: lambda.Code.fromAsset(path.join("./scripts/stat_table_update/")),
      memorySize: 256,
      timeout: cdk.Duration.seconds(15),
      environment: {
        DISCORD_PUBLIC_KEY: discordPublicKey,
        USER_STAT_TABLE: userStatTable.tableName,
        USER_CACHE_TABLE: userCacheTable.tableName,
        steamapikey: steamapikey
      },
    });

    userStatTable.grantReadWriteData(statTableUpdater);

    // Define the Perk Cache Updater Lambda
    const perkCacheUpdater = new lambda.Function(this, 'perkCacheUpdater', {
      runtime: lambda.Runtime.PYTHON_3_8,
      handler: 'perk_cache_update.handler',
      code: lambda.Code.fromAsset(path.join("./scripts/perk_cache_update/")),
      memorySize: 256,
      timeout: cdk.Duration.seconds(10),
      environment: {
        DYNAMODB_TABLE_NAME: perkTable.tableName,
      },
    });

    perkTable.grantReadWriteData(perkCacheUpdater);

    // CloudWatch Event Rules
    const statTableEventRule = new events.Rule(this, 'statTableEventRule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '10', weekDay: 'SUN-SAT' }), // Trigger every day at 2:00 AM Pacific Time
    });

    statTableEventRule.addTarget(new targets.LambdaFunction(statTableUpdater));

    const perkCacheEventRule = new events.Rule(this, 'perkCacheEventRule', {
      schedule: events.Schedule.cron({ minute: '0', hour: '12', weekDay: 'SUN-SAT' }), // Trigger every day at 4:00 AM Pacific Time
    });
  
    perkCacheEventRule.addTarget(new targets.LambdaFunction(perkCacheUpdater));

    new cdk.CfnOutput(this, "FunctionUrl", {
      value: functionUrl.url,
    });
  }
}
