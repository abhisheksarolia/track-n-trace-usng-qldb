from time import sleep
from datetime import datetime
from decimal import Decimal
from boto3 import client
from common import convert_object_to_ion, to_base_64, create_qldb_driver
from pyqldb.driver.qldb_driver import QldbDriver
import json
import os


qldb_client = client('qldb')

ledger_name = os.environ.get('LedgerNameString')


def update_items_with_coldchain(driver,table_name, document, fieldname , fieldvalue):
    print('First Checking if record exist or not') 
    
    statement = "SELECT metadata.id , data.Storage.MaxTemperature, data.Storage.MinTemperature, data.PackageSeal FROM _ql_committed_{} As p WHERE p.data.{} = '{}' AND p.data.ItemSpecifications.MfgBatchNumber = '{}'".format(table_name,fieldname, fieldvalue, document.get('batch'))
    
    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
    
    # Check if there is any record in the cursor
    first_record = next(cursor, None)
    doccount = 0
    sensor_temp = document.get('temperature')
    return_msg = ''
   

    if first_record:
        
        
        print("Existing record found, initiating document update processing..")
        
        for eachrow in cursor:
            doc_id = eachrow['id']
            max_temp = eachrow['MaxTemperature']
            min_temp = eachrow['MinTemperature']
            pkg_seal = eachrow['PackageSeal']
            
            if sensor_temp > max_temp or sensor_temp < min_temp:
                # item coldchain is broken, update document seal & transaction ledger
                pkg_seal = 0
                doccount = doccount + 1
                statement = "UPDATE {} As u SET u.PackageSeal = '{}' WHERE u.PackageLabel = '{}' AND u.ItemSpecifications.MfgBatchNumber = '{}'".format(table_name,pkg_seal, fieldvalue,document.get('batch'))
                print(statement)
                cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
                
                if next(cursor, None):
                    print('Updated package seal for - {}'.format(doc_id))
                
               
        if doccount > 0:
            print('Package coldchain successfully updated') 
        else:
            print("Temperature in permissible range, hence skipped update!")
    else:
        print("No existing record found!")
        


def lambda_handler(event, context):
    
    # Read the event paylaod from IoT sensor
    print(event)
    
    processingerror = False
    return_msg = ''
    batch = event.get('batch')
    package = event.get('package')
    temp_reading = event.get('temperature')

    
    try:
        with create_qldb_driver(ledger_name) as driver:
            update_items_with_coldchain(driver,"Item", event, 'PackageLabel' , package)
            
        print('All processing successfully completed')
    
    except Exception as e:
            processingerror = True
            print('Error inserting or updating documents- {}'.format(e))
            
    