/*
 * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
 * SPDX-License-Identifier: MIT-0
 *
 * Permission is hereby granted, free of charge, to any person obtaining a copy of this
 * software and associated documentation files (the "Software"), to deal in the Software
 * without restriction, including without limitation the rights to use, copy, modify,
 * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
 * permit persons to whom the Software is furnished to do so.
 *
 * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
 * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
 * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
 * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
 * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
 * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
 */

import { Duration, Stack, StackProps, RemovalPolicy, CfnOutput } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cr from 'aws-cdk-lib/custom-resources'
import * as cognito from 'aws-cdk-lib/aws-cognito'
import * as iot from 'aws-cdk-lib/aws-iot';

export class TrackntraceCdkStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    // Code for solution starts here 
    const ledgerName = 'trackntrace-using-qldb'
    const start = Date.now().toString()
    // ** IAM role for Ledger processing
    const ledgerProcessingRole = new iam.Role(this, 'ledger-processing-role', {
      roleName: 'ledger-processing-role',
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com')
    });
    
    // ** Assign relevant IAM policies to the role
    ledgerProcessingRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("service-role/AWSLambdaBasicExecutionRole"));
    ledgerProcessingRole.addManagedPolicy(iam.ManagedPolicy.fromAwsManagedPolicyName("AmazonQLDBFullAccess"));
    
    // Shared lib layer 
    const lambdaSharedLibLayer = new lambda.LayerVersion(this, 'lambda-shared-lib-layer', {
      layerVersionName: 'lambda-shared-lib-layer',
      removalPolicy: RemovalPolicy.DESTROY,
      code: lambda.Code.fromAsset('sharedLib'),
      compatibleArchitectures: [lambda.Architecture.X86_64],
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_7]
    });

    // Shared Files layer 
    const lambdaSharedFileLayer = new lambda.LayerVersion(this, 'lambda-shared-file-layer', {
      layerVersionName: 'lambda-shared-file-layer',
      removalPolicy: RemovalPolicy.DESTROY,
      code: lambda.Code.fromAsset('sharedFiles'),
      compatibleArchitectures: [lambda.Architecture.X86_64],
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_7]
    });
    
    // ** Processing lambda to create and initialize ledger with index and tables
    const ledgerInitializer = new lambda.Function(this, 'ledger-initializer', {
      runtime: lambda.Runtime.PYTHON_3_7,
      code: lambda.Code.fromAsset('lambda/ledgerInitializer'),
      handler: 'lambda_function.lambda_handler',
      functionName: 'ledger-initializer',
      layers: [lambdaSharedLibLayer, lambdaSharedFileLayer],
      role: ledgerProcessingRole,
      timeout: Duration.seconds(300),
      environment: {
        'LedgerNameString': ledgerName
      },
    });
    
    // ** Use AWS Custom resource provider to execute QLDB ledger initialization lambda function 
    const lambdaTrigger = new cr.AwsCustomResource(this, 'StatefunctionTrigger', {
      policy: cr.AwsCustomResourcePolicy.fromStatements([new iam.PolicyStatement({
        actions: ['lambda:InvokeFunction'],
        effect: iam.Effect.ALLOW,
        resources: [ledgerInitializer.functionArn]
      })]),
      timeout: Duration.minutes(15),
      onCreate: {
        service: 'Lambda',
        action: 'invoke',
        parameters: {
          FunctionName: ledgerInitializer.functionName,
          InvocationType: 'Event'
        },
        physicalResourceId: cr.PhysicalResourceId.of('JobSenderTriggerPhysicalId')
      }
    })
    lambdaTrigger.node.addDependency(ledgerInitializer, ledgerProcessingRole, lambdaSharedLibLayer, lambdaSharedFileLayer)    
    
    // ** Processing lambda to get ledger operational status 
    const ledgerDescriber = new lambda.Function(this, 'ledger-describer', {
      runtime: lambda.Runtime.PYTHON_3_7,
      code: lambda.Code.fromAsset('lambda/ledgerDescriber'),
      handler: 'lambda_function.lambda_handler',
      functionName: 'ledger-describer',
      layers: [lambdaSharedLibLayer, lambdaSharedFileLayer],
      role: ledgerProcessingRole,
      timeout: Duration.seconds(300),
    });
    
    // ** Processing lambda to create and seed item table on ledger with dummy records
    const itemCreator = new lambda.Function(this, 'item-creator', {
      runtime: lambda.Runtime.PYTHON_3_7,
      code: lambda.Code.fromAsset('lambda/itemCreator'),
      handler: 'lambda_function.lambda_handler',
      functionName: 'item-creator',
      layers: [lambdaSharedLibLayer, lambdaSharedFileLayer],
      role: ledgerProcessingRole,
      timeout: Duration.seconds(300),
      environment: {
        'LedgerNameString': ledgerName
      },
    });  

    // ** Processing lambda to update package details on ledger item table
    const itemUpdate = new lambda.Function(this, 'item-update', {
      runtime: lambda.Runtime.PYTHON_3_7,
      code: lambda.Code.fromAsset('lambda/itemUpdate'),
      handler: 'lambda_function.lambda_handler',
      functionName: 'item-update',
      layers: [lambdaSharedLibLayer, lambdaSharedFileLayer],
      role: ledgerProcessingRole,
      timeout: Duration.seconds(300),
      environment: {
        'LedgerNameString': ledgerName
      },
    });    
    
    // ** Processing lambda to get product details from ledger with validations
    const itemGet = new lambda.Function(this, 'item-get', {
      runtime: lambda.Runtime.PYTHON_3_7,
      code: lambda.Code.fromAsset('lambda/itemGet'),
      handler: 'lambda_function.lambda_handler',
      functionName: 'item-get',
      layers: [lambdaSharedLibLayer, lambdaSharedFileLayer],
      role: ledgerProcessingRole,
      timeout: Duration.seconds(300),
      environment: {
        'LedgerNameString': ledgerName
      },
    });    
    
    // ** Processing lambda to validate details from ledger
    const dataValidation = new lambda.Function(this, 'data-validation', {
      runtime: lambda.Runtime.PYTHON_3_7,
      code: lambda.Code.fromAsset('lambda/dataValidation'),
      handler: 'lambda_function.lambda_handler',
      functionName: 'data-validation',
      layers: [lambdaSharedLibLayer, lambdaSharedFileLayer],
      role: ledgerProcessingRole,
      timeout: Duration.seconds(300),
      environment: {
        'LedgerNameString': ledgerName
      },
    });    
    
    // ** Processing lambda for sensor update
    const sensorUpdate = new lambda.Function(this, 'sensor-update', {
      runtime: lambda.Runtime.PYTHON_3_7,
      code: lambda.Code.fromAsset('lambda/sensorUpdate'),
      handler: 'lambda_function.lambda_handler',
      functionName: 'sensor-update',
      layers: [lambdaSharedLibLayer, lambdaSharedFileLayer],
      role: ledgerProcessingRole,
      timeout: Duration.seconds(300),
      environment: {
        'LedgerNameString': ledgerName
      },
    });  
    
    sensorUpdate.addPermission('AWS IoT rule invocation', {
      principal: new iam.ServicePrincipal('iot.amazonaws.com'),
    });

  // Create the User Pool for the App
    const userPool = new cognito.UserPool(this, 'trackntrace-userpool', {
      removalPolicy: RemovalPolicy.DESTROY,
      userPoolName: 'trackntrace-userpool'+'-'+start,
      signInCaseSensitive: false, // case insensitive is preferred in most situations
      selfSignUpEnabled: true,
      userVerification: {
        emailSubject: 'Verify your email - trackntrace!',
        emailBody: 'Thanks for signing up to our awesome app! Your verification code is {####}',
        emailStyle: cognito.VerificationEmailStyle.CODE
      },
      signInAliases: { username: false, email: true },
      autoVerify: { email: true},
      passwordPolicy: {
        minLength: 12,
        requireLowercase: true,
        requireUppercase: true,
        requireDigits: true,
        requireSymbols: true
      },
      accountRecovery: cognito.AccountRecovery.EMAIL_ONLY
    });
    
    // Add the Cognito domain to user pool 
    const domain = userPool.addDomain('CognitoDomain', {
      cognitoDomain: {
        domainPrefix: 'trackntrace'+'-'+start,
      },
    });
    
    const appClient = userPool.addClient('postman-app-client',{
        userPoolClientName : 'postman-app-client'+'-'+start,
        refreshTokenValidity: Duration.days(30),
        accessTokenValidity: Duration.minutes(60),
        idTokenValidity: Duration.minutes(60),
        generateSecret: true,
        authFlows: {
          userPassword: true,
        },
        oAuth: {
          flows: {
            authorizationCodeGrant: true,
            implicitCodeGrant: true,
          },
          scopes: [ cognito.OAuthScope.PHONE,cognito.OAuthScope.EMAIL,cognito.OAuthScope.OPENID,cognito.OAuthScope.PROFILE ],
          callbackUrls: [
            'https://oauth.pstmn.io/v1/callback',
          ],
          logoutUrls: [ 'https://www.postman.com' ],
        }
    });
    
    const signInUrl = domain.signInUrl(appClient, {
      redirectUri: 'https://oauth.pstmn.io/v1/callback', // must be a URL configured under 'callbackUrls' with the client
    });

    // REST API for API GATEWAY 
    const auth = new apigw.CognitoUserPoolsAuthorizer(this, 'trackntraceAuthorizer', {
      cognitoUserPools: [userPool]
    });

    const api = new apigw.RestApi(this, 'TracknTraceApi', {
      restApiName: 'TracknTraceApi'+'-'+start,
      cloudWatchRole: true,
      defaultCorsPreflightOptions: {
        allowOrigins: [ '*' ],
      },
    });
  
    const trkntrcResource = api.root.addResource('trackntrace');
    const ledgerResource = trkntrcResource.addResource('ledger'); // GET with querystring , POST
    ledgerResource.addMethod('GET', new apigw.LambdaIntegration(ledgerDescriber,{allowTestInvoke:true}))
    ledgerResource.addMethod('POST', new apigw.LambdaIntegration(ledgerInitializer,{allowTestInvoke:true}))
    const productResource = trkntrcResource.addResource('product');
    productResource.addMethod('POST', new apigw.LambdaIntegration(itemCreator,{allowTestInvoke:true}))
    productResource.addMethod('PUT', new apigw.LambdaIntegration(itemUpdate,{allowTestInvoke:true}))
    productResource.addMethod('GET', new apigw.LambdaIntegration(itemGet,{allowTestInvoke:true}))
    
    const validateResource = trkntrcResource.addResource('validate');  // POST - verify paylod for compliance and coldchain
    validateResource.addMethod('POST', new apigw.LambdaIntegration(dataValidation,{allowTestInvoke:true}))
    const simulateResource = trkntrcResource.addResource('simulate');  // POST - sensor payload for coldchain update
    simulateResource.addMethod('POST', new apigw.LambdaIntegration(sensorUpdate,{allowTestInvoke:true}))

  // AWS IoT thing and rule 
    const trackntraceSensor = new iot.CfnThing(this, 'trackntraceSensor', /* all optional props */ {
      thingName: 'trackntraceSensor',
    });    
    const querySql = `SELECT data as data, package as package, batch as batch, ${ledgerName} as ledgername FROM 'trkntrcesensortopic'`
    const trkntrceTopicRule = new iot.CfnTopicRule(this, 'trkntrceTopicRule', {
      ruleName: 'trkntrceTopicRule',
      topicRulePayload: {
      actions: [{
        lambda: {
          functionArn: sensorUpdate.functionArn
        },
      }],
      sql: querySql,
      }
    })

    // 👇 create an Output for Ledger Name
    new CfnOutput(this, 'ledgerName', {
      value: ledgerName,
      description: 'The name of the Amazon QLDB ledger'
    });
  }
}
