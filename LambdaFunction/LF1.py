import base64
import boto3
import json
import time
import uuid
import sys
from datetime import datetime
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError
sys.path.append("/opt") 
import cv2

S3_URL = 'Your S3 Bucket URL'
STREAM_ARN = 'Your Stream ARN'
STREAM_NAME = 'Your Stream Name'
COLLECTION_ID = 'Your Collection ID'
WP1_URL = 'Webpage URL for Owner'
WP2_URL = 'Webpage URL for Visitor'
EMAIL_ADDRESS = 'Your Email Address'
BUCKET = 'imagetestcc'
TABLE_VISITOR = 'visitors'
TABLE_PASSCODE = 'passcodes'
EXPIRE_TIME = 300
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    records = event["Records"]
    decoded_data = json.loads(
        base64.b64decode(records[0]["kinesis"]["data"]).decode("utf-8")
    )
    list_all_faces()
    print("#TEST# Decoded data is shown below:")
    print(decoded_data)
    frag_number = decoded_data['InputInformation']['KinesisVideo']['FragmentNumber']
    print('#TEST# fragmentNumber is:' + str(frag_number))
    
    # frag_number = '91343852333181620797252521544941485199929689570'
    # chunk = get_frag_raw_data(frag_number)
    # img = get_img_byte_data(chunk)
    # save_img_to_s3(img, None)
    
    if decoded_data['FaceSearchResponse'] == []:
        print('#TEST#: No faces detected!')
        return ;
    face_to_be_eval = decoded_data['FaceSearchResponse'][0]
    if len(face_to_be_eval['MatchedFaces']) == 0 or face_to_be_eval['MatchedFaces'][0]['Similarity'] < 10:
        # index new face->save to S3->send owner email
        print('#TEST# The exact time when send Email:' + str(time.time()))
        notify_owner(frag_number) 
    else: # indicates that face is known
        face_id = face_to_be_eval['MatchedFaces'][0]['Face']['FaceId']
        if find_in_dynamoDB(face_id, TABLE_VISITOR):
            if find_in_dynamoDB(face_id, TABLE_PASSCODE):
                if otp_expired(face_id):
                    delete_OTP_dynamoDB(face_id)
                else:
                    idle()
            else:
                one_time_password = generate_OTP(face_id)
                put_OTP_dynamoDB(face_id, one_time_password)
                (visitor_name, visitor_phone) = search_visitor_dynamoDB(face_id)
                time_strings = str(time.time()).split(".") 
                visitor_photo_filename = time_strings[0]
                datetime_object = datetime.now() 
                visitor_photo_timestamp = str(datetime_object)
                chunk = get_frag_raw_data(frag_number)
                visitor_img = get_img_byte_data(chunk)
                save_img_to_s3(visitor_img, visitor_photo_filename)
                photos_array = add_new_photo(BUCKET, visitor_photo_filename, visitor_photo_timestamp, get_photo_array_dynamoDB(face_id))
                update_photo_array_dynamoDB(face_id, photos_array)
                send_SMS_message('+1'+str(visitor_phone), visitor_name, one_time_password, WP2_URL)
        else:
            idle()
    return {
        'statusCode': 200,
        'body': json.dumps('Hello from Lambda!')
    }
    
def notify_owner(visitor_frag_number):
    chunk = get_frag_raw_data(visitor_frag_number)
    visitor_img = get_img_byte_data(chunk)
    visitor_faceId = index_visitor_faces(visitor_img)
    time_strings = str(time.time()).split(".") 
    visitor_photo_filename = time_strings[0]
    save_img_to_s3(visitor_img, visitor_photo_filename)
    datetime_object = datetime.now() 
    visitor_photo_timestamp = str(datetime_object)
    send_email(visitor_faceId, visitor_photo_filename, BUCKET, visitor_photo_timestamp)
    
def idle():
    for i in range(1,5):
        print(i**2)
        
def get_frag_raw_data(frag_number):
    kinesis_client = boto3.client('kinesisvideo')
    response = kinesis_client.get_data_endpoint(
        StreamARN=STREAM_ARN,
        APIName='GET_MEDIA_FOR_FRAGMENT_LIST'
    )
    # print(response['DataEndpoint'])
    
    video_client = boto3.client('kinesis-video-archived-media',
                            endpoint_url=response['DataEndpoint']
                            )
    stream = video_client.get_media_for_fragment_list(
        StreamName=STREAM_NAME,
        Fragments=[
            frag_number
        ]
    )
    chunk = stream['Payload'].read()
    return chunk

def get_img_byte_data(chunk):
    with open('/tmp/stream.mkv', 'wb') as f:
        f.write(chunk)
    cap = cv2.VideoCapture('/tmp/stream.mkv')
    ret, frame = cap.read()
    print('#TEST# The number of frames in a chunk:' + str(len(frame)))
    is_success, buffer = cv2.imencode(".jpg", frame)
    cap.release()
    return buffer.tobytes()

def save_img_to_s3(img, file_name):
    s3_client = boto3.client('s3')
    if file_name is None:
        s3_client.put_object(Body=img, Bucket=BUCKET, 
            Key=str(int(time.time())), ContentType='image/jpeg')
    else:
        s3_client.put_object(Body = img, Bucket=BUCKET,
            Key=file_name, ContentType='image/jpeg')

def otp_expired(face_id):
    table_OTP = dynamodb.Table(TABLE_PASSCODE)
    response = table_OTP.query(KeyConditionExpression=Key('faceId').eq(face_id))
    item_array = response['Items']
    record = item_array[0]
    timestamp = float(record['timestamp'])
    if float(time.time()) - timestamp <= EXPIRE_TIME:
        return False
    else:
        return True
    
def index_visitor_faces(visitor_img):
    rekognition_client = boto3.client('rekognition')
    response = rekognition_client.index_faces(
        CollectionId=COLLECTION_ID,
        Image={'Bytes': visitor_img},
        DetectionAttributes=['ALL'],
        MaxFaces=1,
        QualityFilter='AUTO'
    )
    faceId = response['FaceRecords'][0]['Face']['FaceId']
    print('#TEST# The face ID is:' + str(faceId))
    return faceId
    
def list_all_faces():
    rekognition_client = boto3.client('rekognition')
    response = rekognition_client.list_faces(
        CollectionId=COLLECTION_ID,
        MaxResults=20
    )
    print('#TEST# The faces in collection are:')
    print(response)

def send_email(faceId, file_name, bucket_name, time_stamp):
    temp_WP1_URL = WP1_URL + '#' + faceId + '&' + file_name + '&' + bucket_name + '&' + time_stamp
    temp_S3_URL = S3_URL + '/' + file_name
    BODY_HTML = """
    <html>
    <head>
    </head>
    <body>
      <p>
      Hi,<br/>
      <br/>
      Smart Door has detected an unknown visitor and the following is the snapshot:<br/></p>
      <div align="center">
      <img src=\"""" + temp_S3_URL + """\", alt=\"jojo\" width="640px", height="480px"></div>
      <p>
      If you want to grant permission to enter to this visitor, please click the following link to complete the registration.<br/></p>
      <br/>
      <a href=\"""" + temp_WP1_URL + """"\">Smart Door Registration</a>
    </body>
    </html>
                """
    SES_client = boto3.client('ses')
    response = SES_client.send_email(
        Source=EMAIL_ADDRESS,
        Destination={'ToAddresses': [EMAIL_ADDRESS,]
        },
        Message={
            'Subject': {
                'Charset': 'UTF-8',
                'Data': 'New Visitor Coming'
            },
            'Body': {
                'Text': {
                    'Charset': 'UTF-8',
                    'Data': 'It\'s only a test email!'
                },
                'Html': {
                    'Data': BODY_HTML,
                    'Charset': 'UTF-8'
                }
            }
        }
    )
    print('#TEST# The response of sending Email:')
    print(response)
    
def find_in_dynamoDB(faceId, table_name):
    table_v = dynamodb.Table(table_name)
    response = table_v.query(KeyConditionExpression=Key('faceId').eq(faceId))
    item_array = response['Items']
    if item_array == []:
        return False
    else:
        return True
        
def search_visitor_dynamoDB(faceId):
    table_visitor = dynamodb.Table(TABLE_VISITOR)
    response = table_visitor.query(KeyConditionExpression=Key('faceId').eq(faceId))
    item_array = response['Items']
    record = item_array[0]
    visitor_name = (record['name'])
    visitor_phone = (record['phoneNumber'])
    return (visitor_name, visitor_phone)
    
def put_OTP_dynamoDB(faceId, OTP):
    table_OTP = dynamodb.Table(TABLE_PASSCODE)
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
        
def delete_OTP_dynamoDB(faceId):
    dynamoDB_client = boto3.client('dynamodb')
    response = dynamoDB_client.delete_item(
        Key={
            'faceId': {
                'S': faceId,
            }
        },
        TableName=TABLE_PASSCODE
    )
    print('#TEST# The response of deleting an OTP from dynamoDB:')
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
    
def get_photo_array_dynamoDB(faceId):
    table = dynamodb.Table(TABLE_VISITOR)
    try:
        response = table.get_item(
            Key={
                'faceId': faceId
            }
        )
    except ClientError as e:
        print(e.response['Error']['Message'])
    else:
        item = response['Item']
        photo_array = item['photos']
        print("#TEST# GetItem succeeded:")
        print(item)
        # print(json.dumps(item, indent=4))
        return photo_array

def add_new_photo(bucket, objectKey, createdTimestamp, old_array):
    res_item = dict()
    res_item['bucket'] = bucket
    res_item['objectKey'] = objectKey
    res_item['createdTimestamp'] = createdTimestamp
    old_array.append(res_item)
    return old_array

def update_photo_array_dynamoDB(faceId, new_array):
    table = dynamodb.Table(TABLE_VISITOR)
    response = table.update_item(
        Key={
            'faceId': faceId
        },
        UpdateExpression="set photos=:a",
        ExpressionAttributeValues={
            ':a': new_array
        },
        ReturnValues="UPDATED_NEW"
    )
    print("#TEST# UpdateItem succeeded:")
    print(response)
    
def send_SMS_message(phoneNumber, name, OTP, webpage):
    sns_client = boto3.client("sns", region_name='us-west-2')
    message = 'Hello, {}!\r\nYou are allowed to enter. Please open the following URL in your browser and enter the password below:\r\n {}\r\nYour one-time-password is:\r\n {}\r\n Enjoy your visit!'.format(name, webpage, OTP)
    response = sns_client.publish(
        PhoneNumber=phoneNumber,
        Message=message
    )
    print('#TEST# The response of sending SMS message:')
    print(response)
    
def search_OTP_dynamoDB(one_time_password):
    table = dynamodb.Table('passcodes')
    response = table.query(
        IndexName='OTP-index',
        KeyConditionExpression=Key('OTP').eq(one_time_password)
    )
    if response['Items'] == []:
        return False
    else:
        return True