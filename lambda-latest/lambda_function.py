import boto3
import json
import random

# AWS 리소스 설정
REGION_NAME = "ap-northeast-1"
DYNAMO_TABLE = "tooncraft-latest"

def lambda_handler(event, context):
    try:
        # DynamoDB 클라이언트 초기화
        dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)
        table = dynamodb.Table(DYNAMO_TABLE)
        
        # 요청에서 ID 파라미터 확인
        item_id = None
        
        # 쿼리 파라미터에서 ID 확인
        if 'queryStringParameters' in event and event['queryStringParameters']:
            if 'device_id' in event['queryStringParameters']:
                item_id = event['queryStringParameters']['device_id']
        
        # 경로 파라미터에서 ID 확인 (API Gateway 통합용)
        if not item_id and 'pathParameters' in event and event['pathParameters']:
            if 'device_id' in event['pathParameters']:
                item_id = event['pathParameters']['device_id']
        
        # URL 직접 호출 방식에서 ID 확인 (Lambda 함수 URL 방식) 
        if not item_id and 'rawQueryString' in event:
            query_params = {p.split('=')[0]: p.split('=')[1] for p in event['rawQueryString'].split('&') if '=' in p}
            if 'device_id' in query_params:
                item_id = query_params['device_id']
        
        # ID가 있으면 해당 ID로 항목 검색
        if item_id:
            response = table.get_item(Key={'device_id': item_id})
            
            # ID로 검색한 항목이 없으면 에러 반환
            if 'Item' not in response:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'error': f'Item with ID {item_id} not found'})
                }
            
            # ID로 검색한 항목이 있으면 해당 항목 반환
            item = response['Item']
        else:
            # ID가 없으면 첫 번째 항목 반환
            scan_response = table.scan(Limit=1)
            items = scan_response['Items']
            
            if not items:
                return {
                    'statusCode': 404,
                    'headers': {
                        'Content-Type': 'application/json',
                        'Access-Control-Allow-Origin': '*'
                    },
                    'body': json.dumps({'error': 'No items found in the table'})
                }
            
            # 첫 번째 항목 선택
            item = items[0]
        
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
