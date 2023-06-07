# Build an end-to-end application to track goods in a supply chain using Amazon QLDB

Today, companies build complex and custom mechanisms to achieve traceability inside supply chain systems. Instead of building custom ledger functionality on a traditional database system, you can take advantage of Amazon Quantum Ledger Database (Amazon QLDB) to record the history of each transaction in an immutable way on an Amazon QLDB journal. Amazon QLDB helps eliminate the need to engage in the complex development effort of building your ledger-like functionality in applications. With QLDB, the history of changes to your data is immutable—it can't be altered, updated, or deleted. 

In this post, we propose a solution to address a key challenge in the pharmaceutical supply chain around tracking and validating the authenticity of manufactured drugs that require strict cold chain storage during the entire supply chain. You can adopt these concepts to implement product traceability into other kinds of sophisticated supply chains as well.

The following figure depicts the reference architecture of solution. 

![Architecture](/images/trackntrace_arch.png)

## Prerequisites and Setup

The quick deployment of the solution is using [AWS Cloud Development Kit (AWS CDK)](https://docs.aws.amazon.com/cdk/v2/guide/home.html) to create the resources required for this post, such as [Amazon API Gateway](https://aws.amazon.com/api-gateway/) endpoint, [AWS Lambda](https://aws.amazon.com/lambda/) functions, [Amazon Quantum Ledger Database(Amazon QLDB)](https://aws.amazon.com/qldb/), [AWS Identity and Access Management (IAM)](http://aws.amazon.com/iam) role, related permission policies and optional components - [Amazon Cognito](https://aws.amazon.com/cognito/) user pool, and [AWS IoT](https://aws.amazon.com/iot/) thing with associated rule and permissions. 

You can use [AWS Cloud9](https://docs.aws.amazon.com/cloud9/latest/user-guide/setup-express.html), a cloud-based integrated development environment, to complete the actions or run the setup locally on a Windows or Mac workstation/laptop. If you are running the set up locally then install and configure following toolset – 

* [AWS CLI](https://docs.aws.amazon.com/cli/latest/userguide/getting-started-install.html)
* [Node.js](https://nodejs.org/en/download)
* [Python](https://www.python.org/downloads/release/python-3716/)
* [TypeScript](https://www.npmjs.com/package/typescript)
* [AWS CDK for TypeScript](https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html) 
* [Postman](https://www.postman.com/) or [Curl](https://curl.se/)

We are using AWS Cloud9 to set up and run the project, which comes pre-installed with all the above tooling. Follow below steps for solution setup - 

1)  Clone the code from GitHub repo on Cloud 9 terminal shell
```
git clone https://github.com/abhisheksarolia/track-n-trace-usng-qldb.git

cd track-n-trace-usng-qldb/

git checkout feature/auth
```

2)  The AWS CDK includes a library of AWS constructs called the AWS Construct Library, organized into various modules. The library contains constructs for each AWS service. Install the main CDK package for TypeScript – 
```
npm install aws-cdk-lib  
```
3)  Create new directory & install required dependency modules from the “requirements.txt” using python package manager-
```
mkdir sharedLib
mkdir sharedLib/python

pip install -r requirements.txt -t ./sharedLib/python  
```
4)  Create an IAM role with administrator access and [attach the role on cloud9 instance](https://aws.amazon.com/blogs/security/easily-replace-or-attach-an-iam-role-to-an-existing-ec2-instance-by-using-the-ec2-console/). You can use this [deep link to create the role with administrator access](https://console.aws.amazon.com/iam/home#/roles$new?step=review&commonUseCase=EC2%2BEC2&selectedUseCase=EC2&policies=arn:aws:iam::aws:policy%2FAdministratorAccess).


5)  Validate the CDK version on your Cloud9 instance – 
```
cdk version
```
If the output of above command comes as “2.80.0”, then upgrade the CDK to “2.81.0”
```
npm install -g aws-cdk@2.81.0 --force 
```
Validate the version again to make sure CDK version is upgraded.
```
cdk version 
```
6)  Synthesize the CDK template. 
```
cdk synth
```

The first time you deploy an AWS CDK app into an environment (account/region), you install a “bootstrap stack”. This stack includes resources that are used in the toolkit’s operation. For example, the stack includes an S3 bucket that is used to store templates and assets during the deployment process. 

7)  You can use “cdk bootstrap” command to install the bootstrap stack into an environment – 
```
cdk bootstrap
``` 

8)  Deploy the stack – 
```
cdk deploy
```

> Once the stack deployment completes, verify created resources in the AWS console under CloudFormation stacks with the name “TrackntraceCdkStack”


> For invoking API in this post, we will use Postman but you can invoke API via curl also. Go ahead and install Postman locally from [here](https://www.postman.com/downloads/?utm_source=postman-home).



## Set up IoT sensor & Cognito users

To simulate capturing of pharmaceutical medication temperature data from the smart package (refer to architecture diagram above) in transit. We simulate the sensor device behavior via a script (sensor.py) running on an Amazon EC2-based AWS Cloud9 IDE instance. This script file is inside the /sensorFlow directory in the source code repo project and passes the MQTT message payload on initiation.

The synthesized CloudFormation template used for this post creates and registers the smart package as an AWS IoT thing on AWS IoT Core. However, to communicate with the AWS IoT Core, our script required to be authenticated with AWS IoT Core. For that purpose, create and download the AWS IoT thing key and certificates (device certificate, public key file, private key file, Amazon root CA1) from AWS IoT Core things dashboard as shown in the below steps.

1)	Got to AWS IoT Core dashboard inside your AWS account and click on things on left pane and filter things with “trackntrace”
 
![pic1](/images/Picture%201.png)


2)	Select the thing with name ”trackntraceSensor” and then select “Certificates” tab on the thing view screen 

![pic2](/images/Picture2.png) 

From “Certificate” tab click on “Create Certificate”

 ![pic3](/images/Picture3.png) 



3)	Download certificate and keys from the next screen - 

 ![pic4](/images/Picture4.png) 


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

   
![pic5](/images/Picture5.png) 
 
![pic6](/images/Picture6.png) 

![pic7](/images/Picture7.png) 

 
### Set up system users

All the users on the system needs to register and log in before performing any transactions on the system. For this post we will use Amazon Cognito hosted UI to sign up the system users. Amazon Cognito hosted UI makes it easy for you to add sign-up and sign-in layer on top of your existing applications. Go To Cognito dashboard and select “App integration” to get the hosted UI endpoint from the “App Client List” view – 

 ![pic8](/images/Picture8.png) 
 ![pic9](/images/Picture9.png) 
 ![pic10](/images/Picture10.png) 



On click of hosted UI link, you will be able to sign up into Amazon Cognito user pool with your own credentials. Take a note of these credentials which we will use to sign-in during API authentication for OAuth2.0 tokens via postman client in a while.

 ![pic11](/images/Picture11.png) 


We are using API integration to interact with the system and set up postman client for OAuth 2.0 authorization code flow for our solution. Create a new OAuth 2.0 token in the postman client app with details from your Amazon Cognito pool – 

 ![pic12](/images/Picture12.png) 

Click on “Get New Access Token” to authenticate and get ID token for API invocation as OAuth2.0 authorization header on API requests.

![pic13](/images/Picture13.png) 

## Clean Up:

1. Destroy the resources - 
```
cdk destroy 
```

2. Disable QLDB delete protection from AWS Console and delete that on UI or run below aws CLI command 

```
aws qldb delete-ledger --name trackntrace-using-qldb

```