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

# Functionality to support retrieval for specific Item record

from time import sleep
from datetime import datetime
from decimal import Decimal
from boto3 import client
from common import convert_object_to_ion, block_address_to_dictionary, value_holder_to_string, create_qldb_driver
from verifier import verify_document
from pyqldb.driver.qldb_driver import QldbDriver
from base64 import encode, decode, b64encode, b64decode
import json
from amazon.ion.simpleion import dumps, loads
import ionhash
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
    

def verify_coldchain(driver, ledger_name, package, itemid):
    print('Starting coldchain verification..')
    status = False 
    # Get the current tip of journal in the ledger
    current_tip = get_digest_result(ledger_name)
    digest_bytes = current_tip.get('Digest')    
    digestblock_address = current_tip.get('DigestTipAddress')
    statement = "SELECT r.metadata.id As id, r.blockAddress AS blockAddress FROM history(Item) AS r WHERE r.data.ItemId = '{}' and r.data.PackageLabel = '{}' AND r.data.PackageChain.Status = 'Activated'".format(itemid, package)
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
            status = verified
        except Exception as e:
            print('Error in verifying coldchain on document using QLDB returned proof nodes - {}',format(e))
            status = False
    return status

def verify_batch_compliance(driver, ledger_name, batch, itemid):
    print('Starting batch compliance verification')
    status = False
    # Get the current tip of journal in the ledger
    current_tip = get_digest_result(ledger_name)
    digest_bytes = current_tip.get('Digest')
    digestblock_address = current_tip.get('DigestTipAddress')
    statement = "SELECT r.metadata.id As id, r.blockAddress AS blockAddress FROM history(Item) AS r BY r_id WHERE r.data.ItemId = '{}' and r.data.ItemSpecifications.MfgBatchNumber = '{}' AND r.data.ItemSpecifications.QualityCompliance = 'PASS'".format(itemid, batch)
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
            status = verified
        except Exception as e:
            print('Error in verifying compliance document chain using QLDB returned proof nodes - {}',format(e))
            status = False
    return status

def lambda_handler(event, context):
    processing_error = False
    return_message = ''
    verify_status = False
    if event.get('queryStringParameters') is None:
        return_message = 'Required parameter is missing'
        processing_error = True
    else:
        type_name = event.get('queryStringParameters').get('type')
        type_value = event.get('queryStringParameters').get('value')
    
    if not processing_error:
        try:
            with create_qldb_driver(ledger_name) as driver:
                if type_name == 'item':
                    print("Trying to get details for {} - {}. Processing ...".format(type_name, type_value))
                    statement = "select r.data from _ql_committed_Item As r where r.data.ItemId = '{}'".format(type_value)
                    print(statement)
                    cursor = driver.execute_lambda(lambda executor: executor.execute_statement(statement))
                    item_details = {}
                    for doc in cursor:
                        item_id = doc['data']['ItemId']
                        item_batch = doc['data']['ItemSpecifications']['MfgBatchNumber']
                        item_package = doc['data']['PackageLabel']
                        item_details = doc['data']
                    return_message = item_details
                    verify_status = verify_batch_compliance(driver, ledger_name, item_batch, item_id)
                    if verify_status:
                        quality_message = 'Verified'
                    else:
                        quality_message = 'Not Verified'
                    #Processing for Coldchain
                    verify_status = verify_coldchain(driver, ledger_name, item_package, item_id)
                    if verify_status:
                        coldchain_message = 'Verified'
                    else:
                        coldchain_message = 'Not Verified'
        except Exception as e:
            processing_error = True
            print('Server processing failed during verification due to unexpected error - {}',format(e))
            return_message = 'Server processing failed during verification due to unexpected error - {}',format(e)

    if not processing_error:
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "body": json.dumps({"Data": str(return_message), "QualityCompliance": quality_message, "Coldchain": coldchain_message})
        }
    else:
        return {
            "statusCode": 503,
            "isBase64Encoded": False,
            "body": return_message
        }