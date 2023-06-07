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

# Validate functionality for journal transactions

from time import sleep
from datetime import datetime
from decimal import Decimal
from boto3 import client
from common import convert_object_to_ion, block_address_to_dictionary, create_qldb_driver
from verifier import verify_document
from pyqldb.driver.qldb_driver import QldbDriver
from base64 import encode, decode, b64encode, b64decode
import json
from amazon.ion.simpleion import loads
import os

qldb_client = client('qldb')

ledger_name = os.environ.get('LedgerNameString')

def get_digest_result(name):
    """
    Get the digest of a ledger's journal.

    :type name: str
    :param name: Name of the ledger to operate on.

    :rtype: dict
    :return: The digest in a 256-bit hash value and a block address.
    """
    print("Let's get the current digest of the ledger named {}".format(name))
    result = qldb_client.get_digest(Name=name)
    print(result)
    return result

def get_revision(ledger_name, document_id, block_address, digest_tip_address):
    """
    Get the revision data object for a specified document ID and block address.
    Also returns a proof of the specified revision for verification.

    :type ledger_name: str
    :param ledger_name: Name of the ledger containing the document to query.

    :type document_id: str
    :param document_id: Unique ID for the document to be verified, contained in the committed view of the document.

    :type block_address: dict
    :param block_address: The location of the block to request.

    :type digest_tip_address: dict
    :param digest_tip_address: The latest block location covered by the digest.

    :rtype: dict
    :return: The response of the request.
    """
    result = qldb_client.get_revision(Name=ledger_name, BlockAddress=block_address, DocumentId=document_id,
                                      DigestTipAddress=digest_tip_address)
    return result

def verify_coldchain(driver, ledger_name, package, batch):
    print('Starting coldchain verification..')
    output = ""
    status = False 
    # Get the current tip of journal in the ledger
    current_tip = get_digest_result(ledger_name)
    digest_bytes = current_tip.get('Digest')
    
    digestblock_address = current_tip.get('DigestTipAddress')
    
    print('Fetching all items with revision when coldchain was activated for package - {} and batch - {}, and verifying coldchain revisions on each one by one ..'.format(package, batch))
    
    statement = "SELECT r.metadata.id As id, r.blockAddress AS blockAddress FROM history(Item) AS r WHERE r.data.PackageLabel = '{}' AND r.data.ItemSpecifications.MfgBatchNumber = '{}' AND r.data.PackageChain.Status = 'Activated'".format(package, batch)
    print(statement)
    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
    
    for doc in cursor:
        document_block_address = doc['blockAddress']
        document_id = doc['id']
        
        result = get_revision(ledger_name, document_id, block_address_to_dictionary(document_block_address), digestblock_address)
        
        revision = result.get('Revision').get('IonText')
            
        document_hash = loads(revision).get('hash')
           
        proof = result.get('Proof')
            
        try:
            verified = verify_document(document_hash, digest_bytes, proof)
            if not verified:
                print('Document revision is not verified, data compromised - {}'.format(document_id))
                print('Aborting rest of the verification chain..')
                status = False
                return status
            else:
                print('Success! Coldchain verified for document - {}'. format(document_id))
                status = True
            
            # Fetch latest revision coldchain status to report 
            statement1 = "SELECT r.data.ItemId As id, r.data.PackageChain.Status As status FROM _ql_committed_Item AS r WHERE r.data.PackageLabel = '{}' AND r.data.ItemSpecifications.MfgBatchNumber = '{}' AND r.metadata.id = '{}'".format(package, batch, document_id)
            print(statement1)
            cursor1 = driver.execute_lambda(lambda executor: executor.execute_statement(statement1))
            for docn in cursor1:
                item_id = docn['id']
                status = docn['status']
            if item_id in output:
                #skip
                print("Skipping duplicate")
            else:
                output = output + item_id + " colchain - " + status + ';'
        except Exception as e:
            print('Error in verifying coldchain on document using QLDB returned proof nodes - {}',format(e))
            status = False
            
    return status, output

def verify_batch_compliance(driver, ledger_name, batch):
    print('Starting batch compliance verification..')
    status = False 
    output = ""
    # Get the current tip of journal in the ledger
    current_tip = get_digest_result(ledger_name)
    digest_bytes = current_tip.get('Digest')
    
    digestblock_address = current_tip.get('DigestTipAddress')
 
    print('Fetching all item revisions with QA under batch - {}, and verifying complaince on each one by one ..'.format(batch))
    
    statement = "SELECT r.metadata.id As id, r.blockAddress AS blockAddress FROM history(Item) AS r WHERE r.data.ItemSpecifications.MfgBatchNumber = '{}' AND r.data.ItemSpecifications.QualityCompliance = 'PASS'".format(batch)
    print(statement)
    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
    
    for doc in cursor:
        document_block_address = doc['blockAddress']
        document_id = doc['id']
        
        result = get_revision(ledger_name, document_id, block_address_to_dictionary(document_block_address), digestblock_address)
        
        revision = result.get('Revision').get('IonText')
            
        document_hash = loads(revision).get('hash')
           
        proof = result.get('Proof')
            
        try:
            verified = verify_document(document_hash, digest_bytes, proof)
            if not verified:
                print('Document revision is not verified, data compromised - {}'.format(document_id))
                print('Aborting rest of the verification chain..')
                status = False
                return status
            else:
                print('Success! Compliance verified for document - {}'. format(document_id))
                status = True
            # Fetch latest revision for QA status to report 
            statement1 = "SELECT r.data.ItemId As id, r.data.ItemSpecifications.QualityCompliance As qa FROM _ql_committed_Item AS r WHERE r.data.ItemSpecifications.MfgBatchNumber = '{}' AND r.metadata.id = '{}'".format(batch, document_id)
            print(statement1)
            cursor1 = driver.execute_lambda(lambda executor: executor.execute_statement(statement1))
            for docn in cursor1:
                item_id = docn['id']
                status = docn['qa']
            if item_id in output:
                #skip
                print("Skipping duplicate")
            else:
                output = output + item_id + " Quality Compliance - " + status + ';'            
        except Exception as e:
            print('Error in verifying compliance document chain using QLDB returned proof nodes - {}',format(e))
            status = False
            
    return status, output
    

def lambda_handler(event, context):
    
    # Read the event paylaod for ledgername , batchnumber, package , activity
    
    API_flow = False
    processing_error = False
    return_message = ''
    verify_status = False
    
    if event.get('body') is None:
        # pick from lambda test console payload
        print("AWS Lambda console flow")
        verify_activity = event.get('verify')
    else:
        API_flow = True
        # pick from API request
        body_dict_payload = json.loads(event.get('body'))
        verify_activity = body_dict_payload.get('verify')
    
    try:
        with create_qldb_driver(ledger_name) as driver:
            
            if verify_activity == 'Compliance':
                if API_flow:
                    batches = body_dict_payload.get('data').get('batch')
                else:
                    batches = event.get('data').get('batch')
                
                for eachbatch in batches:
    
                    print("Verifying ledger for Quality compliance on batch - {}. Processing ...".format(eachbatch))
                            
                    verify_status, msg = verify_batch_compliance(driver, ledger_name, eachbatch)
                        
                    if verify_status:
                        return_message = ''+ eachbatch + ': Quality compliance data verified on all items ->' + msg
                    else:
                        return_message = ''+ eachbatch + ': Quality compliance data not verified on all items ->' + msg
            
            if verify_activity == 'Coldchain':
                
                if API_flow:
                    package = body_dict_payload.get('package')
                    batches = body_dict_payload.get('data').get('batch')
                else:
                    package = event.get('package')
                    batches = event.get('data').get('batch') 
                    
                for eachbatch in batches:
    
                    print("Verifying ledger for coldchain on package - {} and batch - {}. Processing ...".format(package, eachbatch))
                            
                    verify_status, msg = verify_coldchain(driver, ledger_name, package, eachbatch)
                        
                    if verify_status:
                        return_message = ''+ eachbatch + ': Coldchain data verified on all items -> ' + msg
                    else:
                        return_message = ''+ eachbatch + ': Coldchain data not verified on all items -> ' + msg
            
    except Exception as e:
            processing_error = True
            print('Server processing failed during verification due to unexpected error - {}',format(e))
            return_message = 'Server processing failed during verification due to unexpected error - {}',format(e)
                
    
    if not processing_error:
            
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "body": return_message
        }
    else:
        return {
            "isBase64Encoded": False,
            "statusCode": 503,
            "body": return_message
        }