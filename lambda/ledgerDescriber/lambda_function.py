from time import sleep
from datetime import datetime
from decimal import Decimal
from boto3 import client
from pyqldb.driver.qldb_driver import QldbDriver
from common import create_qldb_driver 
import json

qldb_client = client('qldb')

LEDGER_CREATION_POLL_PERIOD_SEC = 20
ACTIVE_STATE = "ACTIVE"

def get_ledger_state(ledger_name):
    ledger_status = ''
    ledger_exist = False
    result = ''
    try:
        
        result = qldb_client.describe_ledger(Name=ledger_name)
        if result.get('State') == ACTIVE_STATE:
            ledger_exist = True
            ledger_status = 'ACTIVE'
        else:
            ledger_exist = True
            ledger_status = 'NOT_ACTIVE'
        
    except Exception as e:
        message = '' + str(e)
        if "ResourceNotFoundException" in message:
            ledger_exist = False
        else:
            print(e)
        
    return ledger_exist,ledger_status
    

def lambda_handler(event, context):
    
    processing_error = False
    return_msg = ''
 
    # Check if query strings are passed or not
    
    if event.get('queryStringParameters') is None:
        return_msg = 'Required parameter is missing'
        processing_error = True
    else:
        ledger_name = event.get('queryStringParameters').get('ledgerName')

    if not processing_error:
        
        # Check if ledge is in operational state or not
        
        ledger_exist, ledger_status = get_ledger_state(ledger_name)
    
        if ledger_exist:
            if ledger_status == 'ACTIVE':
                return_msg = 'Ledger is active now and ready for further operation'
            else:
                return_msg = 'Ledger creation in process.. Please wait!'
        else:
            return_msg = 'Ledger with name - {} not exist. Please create new'.format(ledger_name)
            
 
    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        "body": return_msg
    }
    
    return response
    
   
        