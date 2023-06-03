from time import sleep
from datetime import datetime
from decimal import Decimal
from boto3 import client
from constants import Constants
from common import create_qldb_driver 
from pyqldb.driver.qldb_driver import QldbDriver
import json
import os


qldb_client = client('qldb')

LEDGER_CREATION_POLL_PERIOD_SEC = 20
ACTIVE_STATE = "ACTIVE"
ledger_name = os.environ.get('LedgerNameString')


def create_ledger(name):
    """
    Create a new ledger with the specified name.

    :type name: str
    :param name: Name for the ledger to be created.

    :rtype: dict
    :return: Result from the request.
    """
    print("Creating ledger named: {}...".format(name))
    result = qldb_client.create_ledger(Name=name, PermissionsMode='STANDARD')
    print('Success. Ledger state: {}.'.format(result.get('State')))
    return result

def wait_for_active(name):
    """
    Wait for the newly created ledger to become active.

    :type name: str
    :param name: The ledger to check on.

    :rtype: dict
    :return: Result from the request.
    """
    print('Waiting for ledger to become active...')
    while True:
        result = qldb_client.describe_ledger(Name=name)
        if result.get('State') == ACTIVE_STATE:
            print('Success. Ledger is active and ready to use.')
            return result
        print('The ledger is still creating. Please wait...')
        sleep(LEDGER_CREATION_POLL_PERIOD_SEC)


def create_table(driver, table_name):
    """
    Create a table with the specified name.

    :type driver: :py:class:`pyqldb.driver.qldb_driver.QldbDriver`
    :param driver: An instance of the QldbDriver class.

    :type table_name: str
    :param table_name: Name of the table to create.

    :rtype: int
    :return: The number of changes to the database.
    """
    print("Creating the '{}' table...".format(table_name))
    statement = 'CREATE TABLE {}'.format(table_name)
    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
    print('{} table created successfully.'.format(table_name))
    return len(list(cursor))

def create_index(driver, table_name, index_attribute):
    """
    Create an index for a particular table.

    :type driver: :py:class:`pyqldb.driver.qldb_driver.QldbDriver`
    :param driver: An instance of the QldbDriver class.

    :type table_name: str
    :param table_name: Name of the table to add indexes for.

    :type index_attribute: str
    :param index_attribute: Index to create on a single attribute.

    :rtype: int
    :return: The number of changes to the database.
    """
    print("Creating index on '{}'...".format(index_attribute))
    statement = 'CREATE INDEX on {} ({})'.format(table_name, index_attribute)
    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
    return len(list(cursor))


def lambda_handler(event, context):
    
    # API_flow = False
    processing_error = False
    return_msg = ''
    print(event)
    
    """
    Create a ledger and wait for it to be active.
    """
    try:
        create_ledger(ledger_name)
        wait_for_active(ledger_name)
    except Exception as e:
        processing_error = True
        print('Unable to create the ledger! - {}'.format(e))
        return_msg = 'Unable to create the ledger! - {}'.format(e)
        #raise e
        
    if not processing_error:
        #proceed ahead
        
        """
        Create required tables, Indexes
        """
        try:
            with create_qldb_driver(ledger_name) as driver:
                
                print('Creating tables on ledger...')
                
                create_table(driver, Constants.ITEM_TABLE_NAME)
                create_table(driver, Constants.SENSOR_TABLE_NAME)
                
                print('Tables created successfully.')
                
                print('Now, creating Indexes ..')
                create_index(driver, Constants.ITEM_TABLE_NAME, Constants.ITEM_ID_INDEX_NAME)
                create_index(driver, Constants.ITEM_TABLE_NAME, Constants.ITEM_MFG_BATCH_NUMBER_INDEX_NAME)
                create_index(driver, Constants.ITEM_TABLE_NAME, Constants.ITEM_PKG_LABEL_INDEX_NAME)
                create_index(driver, Constants.SENSOR_TABLE_NAME, Constants.SENSOR_ID_INDEX_NAME)
                
                print('Index creation completed')        
                
        except Exception as e:
            processing_error = True
            print('Ledger Initialization process failed - {}',format(e))
            return_msg = 'Ledger Initialization process failed - {}',format(e)
            

    if not processing_error:
        return_msg = "Ledger Initialization completed successfully"
        
        
    response = {
        "isBase64Encoded": "false",
        "statusCode": 200,
        "body": return_msg
    }
    
    return response