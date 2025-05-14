import boto3
import json
import re
import random
from datetime import datetime

from genai_kit.aws.amazon_image import BedrockAmazonImage, ImageParams, NovaImageSize
from genai_kit.aws.bedrock import BedrockModel
from genai_kit.aws.claude import BedrockClaude
from genai_kit.aws.embedding import BedrockEmbedding
from opensearchpy import OpenSearch, RequestsHttpConnection
from boto3.dynamodb.types import TypeDeserializer

canvas = BedrockAmazonImage(modelId=BedrockModel.NOVA_CANVAS)
REGION_NAME = "ap-northeast-1"
opensearch_index = 'hur-resto'
opensearch_endpoint = 'https://search-hur-resto-vm43dk4lexqui6474vojkfuyhy.aos.ap-northeast-1.on.aws'
dynamodb = boto3.client(
    'dynamodb',
    region_name=REGION_NAME,
)

image_bucket_name = 'toon-craft-gen-imgs-v2'
video_bucket_name = 'tooncraft-videos-v2'

image_cf = 'https://d2w79zoxq32d33.cloudfront.net'
video_cf = 'https://d3dybxg1g4fwkj.cloudfront.net'

default_urls = [
        "https://d3dybxg1g4fwkj.cloudfront.net/multi_shot_automated_2/120_Doenjang_Jjigae_1_ingredients_5_20250414_202423_20250506_114301/dygsdxd00vro/shot_0004.mp4",
        "https://d2w79zoxq32d33.cloudfront.net/familiar-15-menus2/120_Doenjang_Jjigae_2_preparation_4_20250414_202518.png",
        "https://d2w79zoxq32d33.cloudfront.net/familiar-15-menus2/120_Doenjang_Jjigae_3_cooking_4_20250414_202623.png",
        "https://d3dybxg1g4fwkj.cloudfront.net/multi_shot_automated_2/120_Doenjang_Jjigae_4_plating_3_20250414_202723_20250506_115350/qpnyuhqrjhwh/shot_0002.mp4"
]

embedding_client = BedrockEmbedding()

oss_client = OpenSearch(
            hosts=[{'host': opensearch_endpoint.replace('https://', ''), 'port': 443}],
            http_auth=("yoo", "Integra1!"),
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=300
        )

REGION_NAME = "ap-northeast-1"
CF_DOMAIN = "https://d1z4gor1v1vm43.cloudfront.net"
DYNAMO_TABLE = "hur-resto-500"
S3_OUTPUT_BUCKET = "toon-craft-media"

def extract_json(str):
    try:
        str = str.replace('```json', '').replace('```', '')
        return json.loads(str)
    except Exception as e:
        print(f"Error: {str}")
        return {}
    
def extract_txt_block(text):
    pattern = r"```txt(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    return ""

def deserialize_dynamodb_item(item):
    """Convert DynamoDB item to Python dictionary"""
    return {k: TypeDeserializer().deserialize(v) for k, v in item.items()}

def get_image_url(path):
    """Convert image path to CloudFront URL"""
    return f"{CF_DOMAIN}/{path}"

def vector_search(vector, k: int = 3):
    res = oss_client.search(
            index=opensearch_index,
            body={
                "query": {
                    "knn": {
                        "vector_text": {
                            "vector": vector,
                            "k": k,
                        }
                    }
                },
                "_source": {
                    "excludes": ["vector_text", "vector_image"]
                },
            }
        )
    return res['hits']['hits']

def check_s3_file_exists(bucket_name, key):
    """
    Check if a file exists in S3 bucket
    """
    s3_client = boto3.client('s3')
    try:
        s3_client.head_object(Bucket=bucket_name, Key=key)
        return True
    except:
        return False

def get_media_urls(id):
    """
    Get media URLs for a given id from DynamoDB
    Returns URLs for ingredients, preparation, cooking and plating
    """
    try:
        # Query DynamoDB for items with matching id
        response = dynamodb.query(
            TableName='toon_craft_images',
            KeyConditionExpression='id = :id',
            ExpressionAttributeValues={
                ':id': {'S': str(id)}
            }
        )

        if not response.get('Items'):
            print(f"No items found for id: {id}")
            return default_urls

        # Group items by step
        items_by_step = {
            'ingredients': [],  # 1_ingredients (video)
            'preparation': [],  # 2_preparation (image)
            'cooking': [],      # 3_cooking (image)
            'plating': []       # 4_plating (video)
        }

        for item in response['Items']:
            deserialized = deserialize_dynamodb_item(item)
            step = deserialized.get('step')
            
            # Skip items without step information
            if not step:
                continue
                
            # Map step to category
            if step == '1_ingredients':
                items_by_step['ingredients'].append(deserialized)
            elif step == '2_preparation':
                items_by_step['preparation'].append(deserialized)
            elif step == '3_cooking':
                items_by_step['cooking'].append(deserialized)
            elif step == '4_plating':
                items_by_step['plating'].append(deserialized)

        # Randomly select one item from each step and get its cf_uri
        urls = []
        steps = ['ingredients', 'preparation', 'cooking', 'plating']
        for step in steps:
            items = items_by_step[step]
            if items:
                selected_item = random.choice(items)
                urls.append(selected_item.get('cf_uri', ''))
            else:
                print(f"No items found for step: {step}")
                return default_urls

        return urls

    except Exception as e:
        print(f"Error querying DynamoDB: {str(e)}")
        return default_urls

def explain_food_recommendation(persona, selected_episode, qa_pairs, food_data):
    PROMPT_rev = f"""당신은 나의 상황과 감정을 이해하고 음식을 추천하는 위트 있는 AI 큐레이터입니다.

    ### 입력 데이터:
    나의 프로필: {persona}
    선택한 에피소드: {selected_episode}
    추천된 음식: {food_data.get('menu', '')}
    식당 이름: {food_data.get('name', '')}
    식당 음식의 허영만 선생님 의견: {food_data.get('review', '')}

    ### 출력: 아래와 같은 json 형식을 사용하세요:
    서문은 건너뛰고 나의 상황에 맞춘 음식 추천 설명을 작성하세요. reason_1, reason_2, reason_3은 허영만 선생님의 리뷰를 활용하세요.
    이모지는 적절히 사용하되 과하지 않게 사용하세요.
    {{
        "recommendation_result": {{
            "title": "추천 음식과 가게 이름을 포함한 캐치프레이즈 (짧고 임팩트 있는 문장)",
            "description": "이 음식이 내 상황과 감정에 왜 딱 맞는지 설명하세요.",
            "reason_1": "추천 이유 중 첫 번째 항목, 음식의 감성적/정서적 가치 강조",
            "reason_2": "추천 이유 중 두 번째 항목, 음식의 재료나 조리법 등 맛과 관련된 요소 강조",
            "reason_3": "추천 이유 중 세 번째 항목, 음식이 주는 경험적 가치나 상징성 강조"
        }}
    }}
    """
    claude = BedrockClaude(region='us-east-1', modelId=BedrockModel.SONNET_3_7_CR)
    response = claude.converse(text=PROMPT_rev)
    
    # Extract JSON from the response if it exists
    try:
        # Find JSON content between curly braces
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = response[start:end]
            # Parse and return only the JSON part
            return json.dumps(json.loads(json_str), ensure_ascii=False)
        return response
    except:
        return response

def update_recommendation_to_dynamodb(id, item, episode, media_list, persona, questions, recommend, recommend_id, gen_image, result):
    """
    Update the tooncraft DynamoDB table with recommendation data
    """
    try:
        # Create DynamoDB client
        dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)
        table = dynamodb.Table('tooncraft')
        
        # Prepare the item for DynamoDB
        item = {
            'id': id,
            'item': item,
            'episode': episode,
            'media_list': media_list,
            'persona': persona,
            'questions': questions,
            'recommend': recommend,
            'recommend_id': recommend_id,
            'gen_image': gen_image,
            'result': json.loads(result),
        }
        
        # Put item into DynamoDB
        response = table.put_item(Item=item)
        
        print("Successfully updated recommendation in DynamoDB")
        return response
        
    except Exception as e:
        print(f"Error updating DynamoDB: {str(e)}")
        raise e

def lambda_handler(event, context):
    user_id = event.get('user_id', '')
    recommend = event.get('recommend', '')
    persona = event.get('persona', '')
    selected_episode = event.get('selected_episode', '')
    qa_pairs = event.get('qa_pairs', '')
    device_id = event.get('device_id', '1')  # Default to '1' if not provided

    search_keyword = recommend['food_query']
    print(f"search_keyword: {search_keyword}")

    # 초기 null 값으로 데이터 입력
    initial_data = {
        'user_id': user_id,
        'recommend': recommend,
        'persona': persona,
        'device_id': device_id,
        'id': user_id,
        'item': None,
        'episode': None,
        'media_list': None,
        'questions': None,
        'recommend_id': None,
        'gen_image': None,
        'result': None,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)
    table = dynamodb.Table('tooncraft-latest')
    response = table.put_item(Item=initial_data)
    print(f"Initial data inserted: {response}")

    # Get embedding for user input
    user_embedding = embedding_client.embedding_text(search_keyword)

    # Search for similar foods
    similar_foods = vector_search(user_embedding, k=3)
    print(f"similar_foods: {similar_foods}")

    if similar_foods and len(similar_foods) > 0:
        recommended_food = similar_foods[0]
        food_data = recommended_food.get('_source', {}).get('metadata', {})
        print(f"Recommended food: {food_data}")
    else:
        print("No similar foods found")

    id = food_data.get('id', '')
    print(f"id: {id}")

    item = ""
    try:
        dynamodb_client = boto3.client('dynamodb', region_name=REGION_NAME)
        response = dynamodb_client.get_item(
            TableName=DYNAMO_TABLE,
            Key={'id': {'S': id}}
        )
        print(f"response: {response}")
        
        if 'Item' in response:
            item = deserialize_dynamodb_item(response['Item'])
            print(f"Restaurant information: {item}")

    except Exception as e:
        print(f"Error occurred while loading data: {e}")    

    # Get media URLs from DynamoDB
    urls = get_media_urls(id)
    print(f"urls: {urls}")

    # Invoke Gen Image
    # lambda_client = boto3.client('lambda')
    # result = lambda_client.invoke(
    #     FunctionName='toons-craft-gen-image',
    #     InvocationType='Event',
    #     Payload=json.dumps({
    #         "user_id": user_id,
    #         "device_id": device_id,
    #         "episode": selected_episode,
    #         "image_key": f"{user_id}.jpeg"
    #     }, ensure_ascii=False)
    # )
    
    # Update DynamoDB with the recommendation data
    episode = selected_episode
    media_list = [
        urls[0],  # ingredients video
        urls[1],  # preparation image
        urls[2],  # cooking image
        urls[3]   # plating video
    ]
    questions = [
        {
           "question": qa_pairs[0]["question"],
            "answer": qa_pairs[0]["answer"]
        },
        {
            "question": qa_pairs[1]["question"],
            "answer": qa_pairs[1]["answer"]
        },
        {
            "question": qa_pairs[2]["question"],
            "answer": qa_pairs[2]["answer"]
        }
    ]
    
    # Check if generated image exists in S3
    gen_image_key = f"gen_image/{user_id}.jpeg"
    gen_image = f"{image_cf}/gen_image/{user_id}.jpeg"
    
    # if check_s3_file_exists(image_bucket_name, gen_image_key):
    #     gen_image = f"{image_cf}/gen_image/{user_id}.jpeg"
    # else:
    #     gen_image = ""
    
    # send mid data before generating full tokens
    mid_data = {
        'user_id': user_id,
        'recommend': recommend,
        'persona': persona,
        'device_id': device_id,
        'id': user_id,
        'item': item,
        'episode': episode,
        'media_list': media_list,
        'questions': questions,
        'recommend_id': id,
        'gen_image': gen_image,
        'result': None,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)
    table = dynamodb.Table('tooncraft-latest')
    response = table.put_item(Item=mid_data)
    print(f"Mid data inserted: {response}")

    explaination = explain_food_recommendation(persona, selected_episode, qa_pairs, food_data)
    print(f"explaination: {explaination}")
    # Parse the explanation string into a JSON object
    explaination_obj = json.loads(explaination)
    
    info = {
        "img_key": food_data.get('img_key', ''),
        "review": food_data.get('review', ''),
        "name": food_data.get('name', ''),
        "id": food_data.get('id', ''),
        "item": item,
        "urls": urls,
        "explaination": explaination_obj
    }    
    print(f"info: {info}")
    
    result = update_recommendation_to_dynamodb(
        id=user_id,
        item=item,
        episode=episode,
        media_list=media_list,
        persona=persona,
        questions=questions,
        recommend=recommend,
        recommend_id=id,
        gen_image=gen_image,
        result=json.dumps(explaination_obj, ensure_ascii=False)
    )
    
    print(f"device_id: {device_id}")
    print(f"result: {result}")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sending_data = {
        'device_id': device_id,
        'user_id': user_id,
        'id': user_id,
        'item': item,
        'episode': episode,
        'media_list': media_list,
        'persona': persona,
        'questions': questions,
        'recommend': recommend,
        'recommend_id': id,
        'gen_image': gen_image,
        'result': explaination_obj,
        'timestamp': timestamp,
    }
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)
    table = dynamodb.Table('tooncraft-latest')
    response = table.put_item(Item=sending_data)
    print(f"update latest result: {response}")

    # Invoke custom-page lambda function
    lambda_client = boto3.client('lambda')
    result = lambda_client.invoke(
        FunctionName='custom-page',
        InvocationType='Event',
        Payload=json.dumps(sending_data, ensure_ascii=False)
    )
    print(f"result: {result}")
    return {
        'statusCode': 200,
        'body': {
            "user_id": user_id,
            "device_id": device_id,
            "info": info
        }
    }
