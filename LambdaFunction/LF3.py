import time
import boto3
from boto3.dynamodb.conditions import Key

TABLE_NAME = 'passcodes'
dynamodb = boto3.resource('dynamodb')
EXPIRE_TIME = 300

def lambda_handler(event, context):
    # TODO implement
    if event['OTP']:
        one_time_password = event['OTP']
        table = dynamodb.Table(TABLE_NAME)
        response = table.query(
            IndexName='OTP-index',
            KeyConditionExpression=Key('OTP').eq(one_time_password)
        )
        print(response)
        item_array = response['Items']
        if item_array != []:
            record = item_array[0]
            faceId = record['faceId']
            timestamp = float(record['timestamp'])
            present_time = time.time()
            print('#TEST# Present is:' + str(present_time))
            if float(present_time) - timestamp <= EXPIRE_TIME:
                other_table = dynamodb.Table('visitors')
                resp = other_table.query(KeyConditionExpression=Key('faceId').eq(faceId))
                print("#TEST#：");print(resp)
                name = resp['Items'][0]['name']
                # delete_OTP_dynamoDB(faceId)
                return "Hi, "+name+"!\r\nYou enter the room successfully!"
            delete_OTP_dynamoDB(faceId)
        return "Permission denied!"
    else:
        return 'Parameter Error!'
    
def delete_OTP_dynamoDB(faceId):
    dynamoDB_client = boto3.client('dynamodb')
    response = dynamoDB_client.delete_item(
        Key={
            'faceId': {
                'S': faceId,
            }
        },
        TableName=TABLE_NAME
    )
    print('The response of deleting an OTP from dynamoDB:')
    print(response)
