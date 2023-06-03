
Prerequisites and Setup

Following tools are required to run the solution – 
•	Postman
•	AWS CLI etc
•	Check this list in idot proof mechanism 
 
To get started, we create our solution resources using an AWS CloudFormation te 

Follow the deployment steps mentioned on the GitHub repo to create AWS resources mentioned in the architecture. By cloning the repo, you can use AWS Cloud9, a cloud-based integrated development environment, to complete actions or run locally on a Windows or Mac workstation/laptop.

The quick deployment of the solution is using AWS Cloud Development Kit (AWS CDK) to create the resources required for this post, such as Amazon Cognito user pool,  Amazon API Gateway endpoint, AWS Lambda functions, Amazon Quantum Ledger Database(Amazon QLDB),  AWS IoT thing and associated rule, AWS Identity and Access Management (IAM) role, and all related permissions and policies. You can verify created resources in the AWS console under CloudFormation stacks with the name “TrackntraceCdkStack” – 

 

Open the output tab and take note of following resources – 

API endpoint – 
Ledger name - 

Set up IoT sensor & Cognito users

The focus of this post is to show capabilities of Amazon QLDB for implementing traceability in supply chain, thus implementing IoT sensor behavior and auth features are optional. We have added support for AWS IoT & Amazon Cognito to showcase the completeness of the solution approach. If you are interested to see the complete implementation approach then check out the detailed instructions here.   

To simulate capturing of pharmaceutical medication temperature data from the smart package (refer to architecture diagram above) in transit. We simulate the sensor device behavior via a script (sensor.py) running on an Amazon EC2-based AWS Cloud9 IDE instance. This script file is inside the /sensorFlow directory in the source code repo project and passes the MQTT message payload on initiation.

The synthesized CloudFormation template used for this post creates and registers the smart package as an AWS IoT thing on AWS IoT Core. However, to communicate with the AWS IoT Core, our script required to be authenticated with AWS IoT Core. For that purpose, create and download the AWS IoT thing key and certificates (device certificate, public key file, private key file, Amazon root CA1) from AWS IoT Core things dashboard as shown in the below steps.

1)	Got to AWS IoT Core dashboard inside your AWS account and click on things on left pane and filter things with “trackntrace”
 



2)	Select the thing with name ”trackntraceSensor” and then select “Certificates” tab on the thing view screen 

 

From “Certificate” tab click on “Create Certificate”

 



3)	Download certificate and keys from the next screen - 

 


Save the above downloaded certificate and key files inside the /sensorFlow directory. Rename your certificate(.cert) and private key(private.pem.key) as certificate.pem,  and privateKey.pem respectively.

4)	Create new AWS IoT policy “trackntrace-iot-policy” for our thing – 
 
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "iot:Publish",
        "iot:Subscribe",
        "iot:Connect",
        "iot:Receive"
      ],
      "Resource": [
        "*"
      ]
    }
  ]
}

and attach that to our AWS IoT thing(trackntraceSensor) certificate and make the certificate active –

   

 


 



All the users on the system needs to register and log in before performing any transactions on the system. For this post we will use Amazon Cognito hosted UI to sign up the system users. Amazon Cognito hosted UI makes it easy for you to add sign-up and sign-in layer on top of your existing applications. Go To Cognito dashboard and select “App integration” to get the hosted UI endpoint from the “App Client List” view – 

 


 


 

On click of hosted UI link, you will be able to sign up into Amazon Cognito user pool with your own credentials. Take a note of these credentials which we will use to sign-in during API authentication for OAuth2.0 tokens via postman client in a while.

 


We are using API integration to interact with the system and set up postman client for OAuth 2.0 authorization code flow for our solution. Create a new OAuth 2.0 token in the postman client app with details from your Amazon Cognito pool – 

 

Click on “Get New Access Token” to authenticate and get ID token for API invocation as OAuth2.0 authorization header on API requests.
