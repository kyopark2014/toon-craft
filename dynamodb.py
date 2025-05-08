import json
import time
import boto3
import json

from datetime import datetime

def convert_timestr_to_datetime(timestr):
    """
    Convert timestr in format '20250417' or '20250414_202423' to datetime object
    
    Args:
        timestr (str): String in format 'YYYYMMDD' or 'YYYYMMDD_HHMMSS'
        
    Returns:
        datetime: Converted datetime object
    """
    if '_' in timestr:
        # Format: YYYYMMDD_HHMMSS
        date_part, time_part = timestr.split('_')
        year = int(date_part[:4])
        month = int(date_part[4:6])
        day = int(date_part[6:8])
        hour = int(time_part[:2])
        minute = int(time_part[2:4])
        second = int(time_part[4:6])
        return datetime(year, month, day, hour, minute, second)
    else:
        # Format: YYYYMMDD
        year = int(timestr[:4])
        month = int(timestr[4:6])
        day = int(timestr[6:8])
        return datetime(year, month, day)

def wait_for_table_active(dynamodb, tableName, max_attempts=10):
    """
    테이블이 활성 상태가 될 때까지 기다립니다.
    
    Args:
        dynamodb: DynamoDB 클라이언트
        tableName (str): 확인할 테이블 이름
        max_attempts (int): 최대 시도 횟수
        
    Returns:
        bool: 테이블이 활성 상태가 되면 True, 시간 초과시 False
    """
    for attempt in range(max_attempts):
        try:
            response = dynamodb.describe_table(TableName=tableName)
            status = response['Table']['TableStatus']
            print(f"테이블 상태: {status}")
            
            if status == 'ACTIVE':
                print(f"테이블 '{tableName}'이(가) 활성화되었습니다.")
                return True
                
            # 5초 대기
            print(f"테이블이 아직 준비되지 않았습니다. 상태: {status}. 대기 중... ({attempt+1}/{max_attempts})")
            time.sleep(5)
            
        except Exception as e:
            print(f"테이블 상태 확인 중 오류 발생: {e}")
            time.sleep(5)
    
    print(f"최대 시도 횟수 초과. 테이블이 활성화되지 않았습니다.")
    return False

def check_table(tableName: str):
    # DynamoDB 클라이언트 생성
    dynamodb = boto3.client('dynamodb')
    
    try:
        # 테이블 존재 여부 확인
        response = dynamodb.describe_table(TableName=tableName)
        print("existed!")
        return True
    except dynamodb.exceptions.ResourceNotFoundException:
        print("테이블이 존재하지 않습니다. 새로 생성합니다.")
        result = create_table(dynamodb, tableName)
        print(f"테이블 생성 결과: {result}")        
        # 테이블이 활성화될 때까지 기다림
        wait_for_table_active(dynamodb, tableName)
        return True
    except Exception as e:
        print(f"오류 발생: {e}")
        return False

def create_table(dynamodb, tableName: str):
    try:
        # 테이블 생성
        response = dynamodb.create_table(
            TableName=tableName,
            KeySchema=[
                {
                    'AttributeName': 'Id',
                    'KeyType': 'HASH'  # Partition key
                },
                {
                    'AttributeName': 'step_image_id',
                    'KeyType': 'RANGE'  # Sort key
                }
            ],
            AttributeDefinitions=[
                {
                    'AttributeName': 'Id',
                    'AttributeType': 'S'  # String type
                },
                {
                    'AttributeName': 'step_image_id',
                    'AttributeType': 'S'  # String type
                }
            ],
            ProvisionedThroughput={
                'ReadCapacityUnits': 5,
                'WriteCapacityUnits': 5
            }
        )
        print(f"테이블 '{tableName}'이(가) 생성되었습니다.")
        return response
    except Exception as e:
        print(f"테이블 생성 중 오류 발생: {e}")
        return None

def parse_object_name(object_name):
    #objectName = "120_Doenjang_Jjigae_1_ingredients_5_20250414_202423.png"
    #               0       1      2   3        4    5    6       7
    #objectName = "328_Dried_Radish_Green_Set_Meal_1_ingredients_1_20250417.png"

    # .png 확장자 제거
    if object_name.endswith('.png'):
        name = object_name[:-4]
    print(f"name: {name}")

    parts = name.split('_')
    print(f"parts: {parts}")
    
    pos = len(parts)-1
    for i in range(len(parts)):
        print(f"parts[{i}]: {parts[i]}")
        if parts[i].startswith('2025'):
            print(f"parts[i]: {parts[i]}")
            pos = i
            break
    print(f"pos: {pos}")
    # id
    id = parts[0] 
    print(f"id: {id}")
    
    # step_image_id
    step_image_id = parts[pos-3]+'_'+parts[pos-2]+'_'+parts[pos-1] 
    print(f"step_image_id: {step_image_id}")
        
    # create_at
    timestr = ""
    if pos == len(parts)-1:
        timestr = parts[pos]
    else:
        timestr = parts[pos]+'_'+parts[pos+1]
    print(f"timestr: {timestr}")
    create_at = convert_timestr_to_datetime(timestr)
    print(f"create_at: {create_at}")
    
    # image_index
    image_index = parts[pos-3]
    print(f"image_index: {image_index}")
    
    # menu
    menu = ""
    for i in range(1, pos-3):
        # print(f"parts[i]: {parts[i]}")
        menu += parts[i]+' '
    print(f"menu: {menu}")
    
    # s3_uri    
    s3_uri = 's3://toon-craft-gen-imgs/familiar-15-menus/'+object_name
    print(f"s3_uri: {s3_uri}")
    
    # step
    step = parts[pos-3]+'_'+parts[pos-2]
    print(f"step: {step}")
        
    # 분리된 부분을 매핑
    data = {
        'id': id,
        'step_image_id': step_image_id,
        'create_at': str(create_at),
        'image_index': image_index,
        'menu': menu[:len(menu)-1],
        's3_uri': s3_uri,
        'step': step
    }
    
    return data

def put_item(tableName: str, item_data: dict):
    dynamodb = boto3.client('dynamodb')
    dynamodb.put_item(
        TableName=tableName,
        Item={
            'Id': {'S': item_data['id']},
            'step_image_id': {'S': item_data['step_image_id']},
            'create_at': {'S': item_data['create_at']},
            'image_index': {'S': item_data['image_index']},
            'menu': {'S': item_data['menu']},
            's3_uri': {'S': item_data['s3_uri']},
            'step': {'S': item_data['step']}
        }
    )


def get_s3_image_list(bucket_name, prefix):
    """
    Function to retrieve and return a list of objects from the toon-craft-gen-imgs/familiar-15-menus bucket
    """
    # Create S3 client
    s3_client = boto3.client('s3')
      
    try:
        # Get list of objects from S3 bucket
        response = s3_client.list_objects_v2(
            Bucket=bucket_name,
            Prefix=prefix
        )
        
        # Extract object key list
        image_list = []
        if 'Contents' in response:
            for obj in response['Contents']:
                key = obj['Key']
                if key != prefix:  # Exclude the prefix folder itself
                    image_list.append(key)
        
        # Print results
        print("Image list:")
        for image in image_list:
            print(f"- {image}")
            
        return image_list
        
    except Exception as e:
        print(f"Error occurred: {str(e)}")
        return []
    
if __name__ == "__main__":
    tableName = "toontest3"
    print(f"tableName: {tableName}")
    
    # 테이블 존재 여부 확인 및 필요시 생성
    check_table(tableName)

    bucket_name = 'toon-craft-gen-imgs'
    prefix = 'familiar-15-menus2/'
    
    if tableName:
        image_list = get_s3_image_list(bucket_name, prefix)
        print(f"image_list[0]: {image_list[0]}")
        
        for image in image_list:
            #print(f"image: {image}")
            image = image.replace(prefix, '')
            print(f"image: {image}")
            item_data = parse_object_name(image)
            put_item(tableName, item_data)
        
    #objectName = "120_Doenjang_Jjigae_1_ingredients_5_20250414_202423.png"
    #objectName = "328_Dried_Radish_Green_Set_Meal_1_ingredients_1_20250417.png"
    # objectName = "804_Beef_Pancakes_(Yukjeon)_1_ingredients_1_20250414_203618.png"
    # check_table(tableName)
    
    # item_data = parse_object_name(objectName)
    # json_data = json.dumps(item_data, indent=4)
    
    # print("\n파싱된 객체 데이터:")
    # print(json_data)
    
    
