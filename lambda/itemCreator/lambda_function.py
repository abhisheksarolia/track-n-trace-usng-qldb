# /*
#  * Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#  * SPDX-License-Identifier: MIT-0
#  *
#  * Permission is hereby granted, free of charge, to any person obtaining a copy of this
#  * software and associated documentation files (the "Software"), to deal in the Software
#  * without restriction, including without limitation the rights to use, copy, modify,
#  * merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
#  * permit persons to whom the Software is furnished to do so.
#  *
#  * THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
#  * INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
#  * PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
#  * HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
#  * OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
#  * SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.
#  */

# To create & seed dummy data on the ledger table - Item

from time import sleep
from datetime import datetime
from decimal import Decimal
from boto3 import client
from common import convert_object_to_ion, create_qldb_driver, to_base_64
from pyqldb.driver.qldb_driver import QldbDriver
import json
import os

qldb_client = client('qldb')
ledger_name = os.environ.get('LedgerNameString')

def insert_item_document(driver, table_name, document, fieldname , fieldvalue):   
    print('First Checking if record exist or not') 
    statement = "SELECT * FROM {} WHERE {} = '{}'".format(table_name,fieldname, fieldvalue)
    print(statement)
    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
    # Check if there is any record in the cursor
    first_record = next(cursor, None)
    
    if first_record:
        # Record already exists, no need to insert
        print("Existing record, fetching document ID from commited metadata")
        statement = "SELECT metadata.id, metadata.version FROM _ql_committed_{} AS p WHERE p.data.{} = '{}'".format(table_name,fieldname, fieldvalue)
        print(statement)
        cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
        for doc in cursor:
            document_id = doc['id']   
        pass
    else:
        print("Record does not exist")
        print('Inserting documents in the {} table...'.format(table_name))
        statement = 'INSERT INTO {} ?'.format(table_name)
        cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement,convert_object_to_ion(document)))
        
        if next(cursor, None):
            statement = "SELECT metadata.id, metadata.version FROM _ql_committed_{} AS p WHERE p.data.{} = '{}'".format(table_name,fieldname, fieldvalue)
            newcursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
            for doc in newcursor:
                document_id = doc['id']
    # return document_id
    return document_id
  
def lambda_handler(event, context):
    API_flow = False
    processingerror = False
    return_msg = ''
    
    if event.get('body') is None:
        print("lambda console flow")
        batch_number = event.get('item').get('ItemSpecifications').get('MfgBatchNumber')
        unit_count = event.get('item').get('ItemSpecifications').get('MfgUnitCount')
    else:
        API_flow = True
        # pick from API request
        body_dict_payload = json.loads(event.get('body'))
        batch_number = body_dict_payload.get('item').get('ItemSpecifications').get('MfgBatchNumber')
        # Below count is used to seed data of similar item units on the ledger 
        unit_count = body_dict_payload.get('item').get('ItemSpecifications').get('MfgUnitCount')
        
    # Create QLDB driver for item processing
    try:
        with create_qldb_driver(ledger_name) as driver:
            # Fetch the authenticated user email, if invoked via auth flow else use default 
            useremail = ''
            if event.get('requestContext').get('authorizer') is not None:
                if event.get('requestContext').get('authorizer').get('claims') is not None:    
                    useremail = event.get('requestContext').get('authorizer').get('claims').get('email')
                    print('Authorized user email on token - {}'.format(useremail))
                
            for i in range(1,unit_count+1):
                item_id = batch_number+"000"+str(i)
                newitem = {'ItemId':item_id, "PkgOwner": useremail}
                if API_flow:
                    itempayload = body_dict_payload.get('item')
                else:
                    itempayload = event.get('item')
                itempayload.update(newitem)
                print('Preparing to insert document - {}'.format(i))
                doc_id = insert_item_document(driver,"Item", itempayload, 'ItemId' , item_id)
                
    except Exception as e:
        processingerror = True
        print('Error inserting or updating documents- {}',format(e))
    if not processingerror:
        return_msg = "Successfully added Items"
    else:
        return_msg = "Item Add functionality failed"
        
    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        "body": return_msg
    }
    
    return response