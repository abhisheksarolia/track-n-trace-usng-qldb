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

# Functionality to process sensor simulated events

from time import sleep
from datetime import datetime
from decimal import Decimal
from boto3 import client
from common import convert_object_to_ion, to_base_64, create_qldb_driver
from pyqldb.driver.qldb_driver import QldbDriver
import json
import os
import uuid

qldb_client = client('qldb')
ledger_name = os.environ.get('LedgerNameString')

def update_items_with_coldchain(driver,table_name, document, fieldname , fieldvalue):
    processingerror = False
    doccount = 0
    #Log the sensor reading on the ledger tablele
    print('Inserting sensor data in the Sensor table...')
    # create the payload for sensor insert 
    uid = uuid.uuid4()
    payload = {
        "id" : str(uid),
        "batch" : document.get('batch'),
        "package" : document.get('package'),
        "temp" : document.get('data') 
    }
    statement = 'INSERT INTO Sensor ?'
    try:
        cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement,convert_object_to_ion(payload)))
        print("Sensor record added")
    except Exception as e:
        print('Sensor record insert failed - {}'.format(e))
        processingerror = True
            
    if not processingerror:
        print('Fetching Item records for any storage temperature violation..') 
        statement = "SELECT metadata.id , data.Storage.MaxTemperature, data.Storage.MinTemperature, data.PackageSeal FROM _ql_committed_{} As p WHERE p.data.{} = '{}' AND p.data.ItemSpecifications.MfgBatchNumber = '{}'".format(table_name,fieldname, fieldvalue, document.get('batch'))
        print(statement)
        cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
        # Check if there is any record in the cursor
        first_record = next(cursor, None)
        doccount = 0
        if first_record:
            print("Existing item record found for passed package and batch details..")
            print("Validating sensor reported temperature data against individual item storage temperature ..")        
            doccount = 0
            sensor_temp = document.get('data')
            return_msg = ''
            for eachrow in cursor:
                doc_id = eachrow['id']
                max_temp = eachrow['MaxTemperature']
                min_temp = eachrow['MinTemperature']
                pkg_seal = eachrow['PackageSeal']
                
                if sensor_temp > max_temp or sensor_temp < min_temp:
                    # item coldchain is broken, update document seal & transaction ledger
                    pkg_seal = 0
                    doccount = doccount + 1
                    statement = "UPDATE {} As u SET u.PackageSeal = '{}', u.PackageChain.Status = '{}', u.PackageChain.SensorRef = '{}' WHERE u.PackageLabel = '{}' AND u.ItemSpecifications.MfgBatchNumber = '{}'".format(table_name,pkg_seal, "Violated", uid, fieldvalue,document.get('batch'))
                    print(statement)
                    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
                    if next(cursor, None):
                        print('Updated package seal for - {}'.format(doc_id))
                   
            if doccount > 0:
                print('Package coldchain successfully updated') 
            else:
                print("Temperature update Skipped!") 
        else:
            print("No existing item record found for passed package and batch details!")

    return doccount

def lambda_handler(event, context):
    # Read the event paylaod
    processingerror = False
    return_msg = ''
    document = {}
    APIflow = False
    
    if event.get('body') is None:
        print("AWS IoT rule flow")
        batch = event.get('batch')
        package = event.get('package')
        temp_reading = event.get('data')
        document = event
    else:
        print("API Flow")
        APIflow = True
        body_dict_payload = json.loads(event.get('body'))
        batch = body_dict_payload.get('batch')
        package = body_dict_payload.get('package')
        temp_reading = body_dict_payload.get('data')
        document = body_dict_payload
    try:
        with create_qldb_driver(ledger_name) as driver:
            doc_cnt = update_items_with_coldchain(driver,"Item", document, 'PackageLabel' , package)
            print('Updated sensor data for {} documents'.format(doc_cnt))
            if doc_cnt > 0:
                return_msg = 'Item coldchain details successfully updated'
            else:
                return_msg = 'Existing Item record not found for coldchain update'              
    except Exception as e:
            processingerror = True
            print('Error inserting or updating documents- {}'.format(e))
    if not processingerror:
        return_msg = "Sensor data processsing completed"
    else:
        return_msg = "Sensor data processing failed"
        
    if APIflow:
        response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        "body": return_msg
        }
        
        return response