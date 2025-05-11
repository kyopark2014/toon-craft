import boto3
import json
import random

# AWS 리소스 설정
REGION_NAME = "ap-northeast-1"
DYNAMO_TABLE = "tooncraft"

def get_random_item(table):
    # 전체 아이템 수 확인
    count_response = table.scan(Select='COUNT')
    total_items = count_response['Count']
    
    if total_items == 0:
        return {
            'statusCode': 404,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': 'No items found in the table'})
        }
    
    # 랜덤으로 아이템 선택
    scan_response = table.scan()
    items = scan_response['Items']
    
    # 랜덤으로 아이템 하나 선택
    item = random.choice(items)
    return item

def lambda_handler(event, context):
    """
    DynamoDB에서 아이템을 조회하여 JSON 데이터를 반환하는 Lambda 함수
    1. 요청에 id 파라미터가 있으면 해당 ID로 항목 검색
    2. 없으면 랜덤으로 항목 선택
    
    Parameters:
        event (dict): 트리거 이벤트 데이터
        context (LambdaContext): 런타임 정보
        
    Returns:
        dict: Lambda 응답 (JSON 데이터)
    """
    try:
        # DynamoDB 클라이언트 초기화
        dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)
        table = dynamodb.Table(DYNAMO_TABLE)
        
        # 요청에서 ID 파라미터 확인
        item_id = None
        
        # 쿼리 파라미터에서 ID 확인
        if 'queryStringParameters' in event and event['queryStringParameters']:
            if 'id' in event['queryStringParameters']:
                item_id = event['queryStringParameters']['id']
        
        # 경로 파라미터에서 ID 확인 (API Gateway 통합용)
        if not item_id and 'pathParameters' in event and event['pathParameters']:
            if 'id' in event['pathParameters']:
                item_id = event['pathParameters']['id']
        
        # URL 직접 호출 방식에서 ID 확인 (Lambda 함수 URL 방식) 
        if not item_id and 'rawQueryString' in event:
            query_params = {p.split('=')[0]: p.split('=')[1] for p in event['rawQueryString'].split('&') if '=' in p}
            if 'id' in query_params:
                item_id = query_params['id']

        print(f"selected item id: {item_id}")
        
        # ID가 있으면 해당 ID로 항목 검색
        if item_id:
            response = table.get_item(Key={'id': item_id})
            
            # ID로 검색한 항목이 없으면 랜덤으로 항목 선택
            if 'Item' not in response:
                return get_random_item(table)
            
            # ID로 검색한 항목이 있으면 해당 항목 반환
            item = response['Item']
        else:
            # ID가 없으면 랜덤으로 항목 선택
            item = get_random_item(table)
        
        # JSON 형식으로 직접 응답 (변환 없이)
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps(item, ensure_ascii=False)
        }
            
    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({'error': str(e)})
        }