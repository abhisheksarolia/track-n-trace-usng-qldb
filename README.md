# track-n-trace-usng-qldb
track-n-trace-usng-qldb

1. Clone the Repo locally
2. Cd to root of the project path
3. Install the prerequisites for using AWS CDK - https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_prerequisites
4. Install AWS CDK globally using node package manager: npm install -g aws-cdk
5. AWS CDK requires dedicated Amazon S3 buckets and other containers to be available to AWS CloudFormation during deployment. Bootstrap these using below command - 
cdk bootstrap aws://ACCOUNT-NUMBER/REGION

( Here, replace with your respective AWS account and REGION values)
6. This soluton is built against python 3.9 (Follow steps here to install latest stable release for 3.9 - https://tecadmin.net/install-python-3-9-on-amazon-linux/), check installed python version - 
python --version 

6. Install required dependency modules from the “requirements.txt” using python package manager-

pip install -r requirements.txt -t ./sharedLib/python
7. Install the AWS IoT Device SDK for Python - https://docs.aws.amazon.com/greengrass/v1/developerguide/IoT-SDK.html
pip3.9 install awsiotsdk

8. Build the project using cdk synth
9. deploy the project using cdk deploy 
 

Clean Up:

1. Destroy the resources - cdk destroy 
2. Edit QLDB delete protection and delete that 






