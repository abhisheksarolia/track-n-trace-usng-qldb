# track-n-trace-usng-qldb
track-n-trace-usng-qldb

1. Clone the Repo locally
2. Cd to root of the project path
3. Install the prerequisites for using AWS CDK - https://docs.aws.amazon.com/cdk/v2/guide/getting_started.html#getting_started_prerequisites
4. Install AWS CDK globally using node package manager: npm install -g aws-cdk
5. Install CDK package : npm install aws-cdk-lib -g -save (Note: If you created a CDK project using cdk init, you don't need to manually install aws-cdk-lib)

6. This soluton is built against python 3.9 (Follow steps mentioned here - https://realpython.com/installing-python/  to install the specific python release - https://www.python.org/downloads/), check installed python version - 
python3.9 --version 

7. Create new folder path on project root as - sharedLib/python, Install required dependency modules from the “requirements.txt” using python package manager-

pip3.9 install -r requirements.txt -t ./sharedLib/python

8. Install the AWS IoT Device SDK for Python - https://docs.aws.amazon.com/greengrass/v1/developerguide/IoT-SDK.html
pip3.9 install awsiotsdk

9. If using Cloud9 then create IAM role with admin access and attach to cloud9 instance. 

10. AWS CDK requires dedicated Amazon S3 buckets and other containers to be available to AWS CloudFormation during deployment. Bootstrap these using below command - 
cdk bootstrap aws://ACCOUNT-NUMBER/REGION

( Here, replace with your respective AWS account and REGION values)

11. Build the project using cdk synth
12. deploy the project using cdk deploy 
 

Clean Up:

1. Destroy the resources - cdk destroy 
2. Edit QLDB delete protection and delete that 



