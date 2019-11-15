import json
import boto3
import uuid
import time
from datetime import datetime

WP2_URL = 'Webpage URL for Visitor'
db_resource = boto3.resource('dynamodb')
TABLE_VISITOR_NAME = 'visitors'
TABLE_OTP_NAME = 'passcodes'
COLLECTION_ID = 'Your Collection ID'

def lambda_handler(event, context):
    print(event) 
    faceId = event['faceId']
    objectKey = event['objectKey']
    bucket = event['bucket']
    createdTimestamp = event['createdTimestamp']
    if event['name'] and event['phoneNumber'] and str(event['checked']):
        name = event['name']
        phoneNumber = event['phoneNumber']
        checked = event['checked']
        if int(checked) == 0:
            put_visitor_dynamoDB(faceId, name, phoneNumber, objectKey, bucket, createdTimestamp)
            one_time_password = generate_OTP(faceId)
            send_SMS_message('+1'+str(phoneNumber), name, one_time_password, WP2_URL)
            put_OTP_dynamoDB(faceId, one_time_password)
            print('Test message: visitor approved!')
            return "Add visitor successfully!"
        else:
            faces = list()
            faces.append(faceId)
            delete_faceID_from_collection(COLLECTION_ID, faces)
            delete_photo_from_S3(bucket, objectKey)
            print('Test message: visitor denied!')
            return "Deny visitor\'s accesss successfully!"
    else:
        #return{'statusCode' : 403,'body' : json.dumps('Parameter Error!')}
        checked = event['checked']
        if int(checked) == 1:
            faces = list()
            faces.append(faceId)
            delete_faceID_from_collection(COLLECTION_ID, faces)
            delete_photo_from_S3(bucket, objectKey)
            print('Test message: visitor denied!')
            return "Deny visitor\'s accesss successfully!"
        else:
            return "Parameter error! Please enter all information provided!"

def put_visitor_dynamoDB(ID, name, phoneNumber, objectKey, bucket, timestamp):
    table_visitor = db_resource.Table(TABLE_VISITOR_NAME)
    objectKey = str(objectKey) + '.jpg'
    response = table_visitor.put_item(
        Item={
            'faceId': ID,
            'name': name,
            'phoneNumber': phoneNumber,
            'photos': [
                {
                    'objectKey': objectKey,
                    'bucket': bucket,
                    'createdTimestamp': str(timestamp)
                }
            ]
        }
    )
    print('#Test# The response of put Visitor item into dynamoDB:')
    print(response)
    
def put_OTP_dynamoDB(faceId, OTP):
    table_OTP = db_resource.Table(TABLE_OTP_NAME)
    timestamp = time.time()
    response = table_OTP.put_item(
        Item={
            'faceId': faceId,
            'OTP': OTP,
            'timestamp': str(timestamp),
            'expireTimestamp':str(timestamp+300)
        }
    )
    print("#TEST# The response of put OTP item into dynamoDB:")
    print(response)
    
def send_SMS_message(phoneNumber, name, OTP, webpage):
    sns_client = boto3.client("sns", region_name='us-west-2')
    message = 'Hello, {}!\r\nYou are allowed to enter. Please open the following URL in your browser and enter the password below:\r\n {}\r\nYour one-time-password is:\r\n{}\r\nEnjoy your visit!'.format(name, webpage, OTP)
    response = sns_client.publish(
        PhoneNumber=phoneNumber,
        Message=message
    )
    print('#TEST# The response of sending SMS message:')
    print(response)
    
def generate_OTP(faceId):
    OTP = str(uuid.uuid5(uuid.uuid4(), str(faceId)))
    OTP_strings = OTP.split('-')
    new_OTP = OTP_strings[0]
    while search_OTP_dynamoDB(new_OTP):
        OTP = str(uuid.uuid5(uuid.uuid4(), str(faceId)))
        OTP_strings = OTP.split('-')
        new_OTP = OTP_strings[0]
    print('#TEST# One_time_password is:' + new_OTP)
    return new_OTP
    
def delete_faceID_from_collection(collectionId, faceIds):
    rekognition_client = boto3.client('rekognition')
    response = rekognition_client.delete_faces(
        CollectionId=collectionId,
        FaceIds=faceIds
    )
    print("#TEST# The response of delete faceId from Collection:")
    print(response)


def delete_photo_from_S3(bucket_name, object_key):
    s3 = boto3.resource('s3')
    object_summary = s3.ObjectSummary(bucket_name, object_key)
    response = object_summary.delete()
    print("#TEST# The response of delete visitor\'s photo from S3:")
    print(response)
    
def search_OTP_dynamoDB(one_time_password):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table('passcodes')
    response = table.query(
        IndexName='OTP-index',
        KeyConditionExpression=Key('OTP').eq(one_time_password)
    )
    if response['Items'] == []:
        return False
    else:
        return True