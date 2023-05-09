import { Duration, Stack, StackProps, RemovalPolicy } from 'aws-cdk-lib';
import { Construct } from 'constructs';
import * as apigw from 'aws-cdk-lib/aws-apigateway';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as cr from 'aws-cdk-lib/custom-resources'
import * as cognito from 'aws-cdk-lib/aws-cognito'
import * as iot from 'aws-cdk-lib/aws-iot';
// import { HttpUrlIntegration, HttpLambdaIntegration } from '@aws-cdk/aws-apigatewayv2-integrations';
// import { HttpJwtAuthorizer } from '@aws-cdk/aws-apigatewayv2-authorizers';


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
    
    // test code 
    // const testIntegrator = new lambda.Function(this, 'test-integrator', {
    //   runtime: lambda.Runtime.PYTHON_3_9,
    //   code: lambda.Code.fromAsset('lambda/testIntegrator'),
    //   handler: 'lambda_function.lambda_handler',
    //   functionName: 'test-integrator',
    //   role: ledgerProcessingRole,
    //   timeout: Duration.seconds(300),
    //   // environment: {
    //   //   'LedgerNameString': ledgerName
    //   // },
    // });
    
    // Shared lib layer 
    
    const lambdaSharedLibLayer = new lambda.LayerVersion(this, 'lambda-shared-lib-layer', {
      layerVersionName: 'lambda-shared-lib-layer',
      removalPolicy: RemovalPolicy.DESTROY,
      code: lambda.Code.fromAsset('sharedLib'),
      compatibleArchitectures: [lambda.Architecture.X86_64],
      // compatibleRuntimes: [lambda.Runtime.PYTHON_3_9, lambda.Runtime.PYTHON_3_8, lambda.Runtime.PYTHON_3_7]
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9]
    });

    // Shared Files layer 
    
    const lambdaSharedFileLayer = new lambda.LayerVersion(this, 'lambda-shared-file-layer', {
      layerVersionName: 'lambda-shared-file-layer',
      removalPolicy: RemovalPolicy.DESTROY,
      code: lambda.Code.fromAsset('sharedFiles'),
      compatibleArchitectures: [lambda.Architecture.X86_64],
      // compatibleRuntimes: [lambda.Runtime.PYTHON_3_9, lambda.Runtime.PYTHON_3_8, lambda.Runtime.PYTHON_3_7]
      compatibleRuntimes: [lambda.Runtime.PYTHON_3_9]
    });
    
    // ** Processing lambda to create and initialize ledger with index and tables
    
    const ledgerInitializer = new lambda.Function(this, 'ledger-initializer', {
      runtime: lambda.Runtime.PYTHON_3_9,
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
      runtime: lambda.Runtime.PYTHON_3_9,
      code: lambda.Code.fromAsset('lambda/ledgerDescriber'),
      handler: 'lambda_function.lambda_handler',
      functionName: 'ledger-describer',
      layers: [lambdaSharedLibLayer, lambdaSharedFileLayer],
      role: ledgerProcessingRole,
      timeout: Duration.seconds(300),
      // environment: {
      //   'LedgerNameString': ledgerName
      // },
    });
    
    // ** Processing lambda to create and seed item table on ledger with dummy records
    
    const itemCreator = new lambda.Function(this, 'item-creator', {
      runtime: lambda.Runtime.PYTHON_3_9,
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
      runtime: lambda.Runtime.PYTHON_3_9,
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
      runtime: lambda.Runtime.PYTHON_3_9,
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
      runtime: lambda.Runtime.PYTHON_3_9,
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
      runtime: lambda.Runtime.PYTHON_3_9,
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
          // userSrp: true,
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
      // allowHeaders: apigw.Cors.DEFAULT_HEADERS,
      // allowMethods: [ 'GET', 'PUT' ]
    },
    //defaultIntegration: apigw.LambdaIntegration
  });
  
  const trkntrcResource = api.root.addResource('trackntrace');
  const ledgerResource = trkntrcResource.addResource('ledger'); // GET with querystring , POST
  // Test code 
  // ledgerResource.addMethod('GET', new apigw.LambdaIntegration(testIntegrator,{allowTestInvoke:true, 
  //                                 // requestParameters:{"integration.request.querystring.ledgerName" : "method.request.querystring.ledgerName"},
  //                                 //requestTemplates:{ "application/json": "{ \"ledgerName\": \" $input.params('ledgerName')\" }" }
  //                                 }), 
  //   {
  //     authorizer: auth,
  //     authorizationType: apigw.AuthorizationType.COGNITO
      
  //   })
  
  // ledgerResource.addMethod('POST', new apigw.LambdaIntegration(testIntegrator,{allowTestInvoke:true, 
  //                                 // requestParameters:{"integration.request.querystring.ledgerName" : "method.request.querystring.ledgerName"},
  //                                 //requestTemplates:{ "application/json": "{ \"ledgerName\": \" $input.params('ledgerName')\" }" }
  //                                 }), 
  //   {
  //     authorizer: auth,
  //     authorizationType: apigw.AuthorizationType.COGNITO
      
  //   })
  
  ledgerResource.addMethod('GET', new apigw.LambdaIntegration(ledgerDescriber,{allowTestInvoke:true, 
                                  // requestParameters:{"method.request.querystring.ledgerName": "true"},
                                  // requestTemplates:{ "application/json": "{ \"ledgerName\": \" $input.params('ledgerName')\" }" }
                                  }), 
    {
      authorizer: auth,
      authorizationType: apigw.AuthorizationType.COGNITO
      
    })
  ledgerResource.addMethod('POST', new apigw.LambdaIntegration(ledgerInitializer,{allowTestInvoke:true}), 
    {
      authorizer: auth,
      authorizationType: apigw.AuthorizationType.COGNITO
      
    })
  // const loginResource = trkntrcResource.addResource('login'); // POST
  // loginResource.addMethod('POST')
  // const registerResource = trkntrcResource.addResource('register'); // POST 
  // registerResource.addMethod('POST')
  
  const productResource = trkntrcResource.addResource('product');
  
  productResource.addMethod('POST', new apigw.LambdaIntegration(itemCreator,{allowTestInvoke:true}), 
    {
      authorizer: auth,
      authorizationType: apigw.AuthorizationType.COGNITO
      
    })
    
  productResource.addMethod('PUT', new apigw.LambdaIntegration(itemUpdate,{allowTestInvoke:true}), 
    {
      authorizer: auth,
      authorizationType: apigw.AuthorizationType.COGNITO
      
    })
  
  productResource.addMethod('GET', new apigw.LambdaIntegration(itemGet,{allowTestInvoke:true}), 
    {
      authorizer: auth,
      authorizationType: apigw.AuthorizationType.COGNITO
      
    })
    
  const validateResource = trkntrcResource.addResource('validate');  // POST - verify paylod for compliance and coldchain
  
  validateResource.addMethod('POST', new apigw.LambdaIntegration(dataValidation,{allowTestInvoke:true}), 
    {
      authorizer: auth,
      authorizationType: apigw.AuthorizationType.COGNITO
      
    })

// AWS IoT thing and rule 

  const trackntraceSensor = new iot.CfnThing(this, 'trackntraceSensor', /* all optional props */ {
    thingName: 'trackntraceSensor',
  });
  
  const querySql = `SELECT temperature as temperature, package as package, batch as batch, ${ledgerName} as ledgername FROM 'trkntrcesensortopic'`
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
  

  }
}
