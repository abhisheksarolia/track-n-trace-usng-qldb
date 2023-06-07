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

# Processing functionality for updating Item records on journal

from time import sleep
from datetime import datetime
from decimal import Decimal
from boto3 import client
from common import convert_object_to_ion, create_qldb_driver, to_base_64
from pyqldb.driver.qldb_driver import QldbDriver
import json
import os
import uuid

qldb_client = client('qldb')
ledger_name = os.environ.get('LedgerNameString')

def update_item_compliance(driver, table_name, document, fieldname , fieldvalue, data, useremail):
   
    print('First Checking if record exist or not') 
    
    statement = "SELECT metadata.id FROM _ql_committed_{} As p WHERE p.data.ItemSpecifications.QualityCompliance = '' AND p.data.ItemSpecifications.{} = '{}'".format(table_name,fieldname, fieldvalue)
    print(statement)
    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
    # Check if there is any record in the cursor
    first_record = next(cursor, None)
    doccount = 0

    if first_record:
        print("Existing record found, initiating document update processing..")
        statement = "UPDATE {} As u SET u.ItemSpecifications.QualityCompliance = '{}', PkgOwner = '{}' WHERE u.ItemSpecifications.MfgBatchNumber = '{}'".format(table_name,data, useremail,fieldvalue)
        print(statement)
        cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
        doccount = 0
        for doc in cursor:
            doccount = doccount + 1
    else:
        print("No existing record found for compliance update!")
    return doccount
    
def update_item_coldchain(driver,table_name, document, fieldname , fieldvalue, data, useremail):
    print('First Checking if record exist or not') 
    statement = "SELECT metadata.id FROM _ql_committed_{} As p WHERE p.data.{} = '{}' AND p.data.ItemSpecifications.MfgBatchNumber = '{}'".format(table_name,fieldname, fieldvalue, document.get('batch'))
    print(statement)
    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
    # Check if there is any record in the cursor
    first_record = next(cursor, None)
    doccount = 0

    if first_record:
        print("Existing record found, initiating document update processing..")
        statement = "UPDATE {} As u SET u.PackageSeal = '{}', u.PkgOwner = '{}', u.PackageChain.Status = '{}' WHERE u.PackageLabel = '{}' AND u.ItemSpecifications.MfgBatchNumber = '{}'".format(table_name,data, useremail,"Activated",fieldvalue, document.get('batch'))
        print(statement)
        cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
        doccount = 0
        for doc in cursor:
            doccount = doccount + 1
        print(doccount)
    else:
        print("No existing record found for update!")
    # return doccount
    return doccount

def update_item_packaging(driver, table_name, document, fieldname , fieldvalue, useremail):
    print('First Checking if record exist or not') 
    statement = "SELECT metadata.id FROM _ql_committed_{} As p WHERE p.data.{} = '{}'".format(table_name,fieldname, fieldvalue)
    print(statement)
    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
    # Check if there is any record in the cursor
    first_record = next(cursor, None)
    doccount = 0

    if first_record:
        print("Existing record found, initiating document update processing..")
        statement = "UPDATE {} As u SET u.PackageLabel = '{}', u.PkgOwner = '{}' WHERE u.ItemId = '{}' AND u.ItemSpecifications.MfgBatchNumber = '{}'".format(table_name,document.get('package'),useremail ,fieldvalue, document.get('batch'))
        print(statement)
        cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
        doccount = 0
        for doc in cursor:
            doccount = doccount + 1
    else:
        print("No existing record found for update!")
    # return doccount
    return doccount

def lambda_handler(event, context):
    # Read the event paylaod for batch, package , activity, data
    API_flow = False
    processingerror = False
    return_msg = ''
    
    if event.get('body') is None:
        # pick from lambda test payload
        print("lambda console flow")
        batch = event.get('batch')
        package = event.get('package')
        data = event.get('data')
        activity = event.get('activity')
    else:
        API_flow = True
        # pick from API request
        print("API integration flow")
        body_dict_payload = json.loads(event.get('body'))
        batch = body_dict_payload.get('batch')
        package = body_dict_payload.get('package')
        data = body_dict_payload.get('data')
        activity = body_dict_payload.get('activity')
    # Initiate the business processing using QLDB driver object 
    try:
        with create_qldb_driver(ledger_name) as driver:
            # Fetch the authenticated user id, if invoked via auth flow else use default
            useremail = ''
            if event.get('requestContext').get('authorizer') is not None:
                if event.get('requestContext').get('authorizer').get('claims') is not None:    
                    useremail = event.get('requestContext').get('authorizer').get('claims').get('email')
                    print('Authorized user email on token - {}'.format(useremail))
                
            if activity == 'Compliance':
                doc_cnt = 0
                if API_flow:
                    doc_cnt = update_item_compliance(driver,"Item", body_dict_payload, 'MfgBatchNumber' , batch, data, useremail)
                else:
                    doc_cnt = update_item_compliance(driver,"Item", event, 'MfgBatchNumber' , batch, data, useremail)
                print('Updated compliance for {} documents'.format(doc_cnt))
                
                if doc_cnt > 0:
                    return_msg = 'Compliance details successfully updated'
                else:
                    return_msg = 'Existing Item record not found for compliance update'
            
            if activity == 'Package':
                doc_cnt = 0
                if API_flow:
                    doc_cnt = update_item_packaging(driver,"Item", body_dict_payload, 'ItemId' , data, useremail)
                else:
                    doc_cnt = update_item_packaging(driver,"Item", event, 'ItemId' , data, useremail)
                print('Updated packaging for {} documents'.format(doc_cnt))
                if doc_cnt > 0:
                    return_msg = 'Item packaging details successfully updated'
                else:
                    return_msg = 'Existing Item record not found for package update'
                    
            if activity == 'Coldchain':
                doc_cnt = 0
                if API_flow:
                    doc_cnt = update_item_coldchain(driver,"Item", body_dict_payload, 'PackageLabel' , package, data, useremail)
                else:
                    doc_cnt = update_item_coldchain(driver,"Item", event, 'PackageLabel' , package, data, useremail)
                print('Updated coldchain for {} documents'.format(doc_cnt))
                if doc_cnt > 0:
                    return_msg = 'Item coldchain details successfully updated'
                else:
                    return_msg = 'Existing Item record not found for coldchain update'                
    except Exception as e:
        processingerror = True
        print('Error updating documents- {}'.format(e))
        return_msg = 'Error updating documents- {}'.format(e)        

    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        "body": return_msg
    }
    
    return response