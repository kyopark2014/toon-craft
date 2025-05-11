import boto3
import json
import re
import random

from genai_kit.aws.amazon_image import BedrockAmazonImage, ImageParams, NovaImageSize
from genai_kit.aws.bedrock import BedrockModel
from genai_kit.aws.claude import BedrockClaude
from genai_kit.aws.embedding import BedrockEmbedding
from opensearchpy import OpenSearch, RequestsHttpConnection
from boto3.dynamodb.types import TypeDeserializer

canvas = BedrockAmazonImage(modelId=BedrockModel.NOVA_CANVAS)
REGION_NAME = "ap-northeast-1"
opensearch_index = 'hur-resto'
# opensearch_endpoint = 'https://search-hur-restaurants-dev-oww5qyphshcdrsh2sqizoqkdh4.aos.ap-northeast-1.on.aws'
opensearch_endpoint = 'https://search-hur-resto-vm43dk4lexqui6474vojkfuyhy.aos.ap-northeast-1.on.aws'
dynamodb = boto3.client(
    'dynamodb',
    region_name=REGION_NAME,
)

image_bucket_name = 'toon-craft-gen-imgs-v2'
video_bucket_name = 'tooncraft-videos-v2'
image_prefix = 'familiar-15-menus2/'
# video_prefix = 'multi_shot_automated_2/'
video_prefix = 'single/familiar-15-menus2/'

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

def get_s3_list(bucket_name, prefix):
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

image_list = get_s3_list(image_bucket_name, prefix=image_prefix)
print(f"image_list: {image_list}")

video_list = get_s3_list(video_bucket_name, prefix=video_prefix)
print(f"video_list: {video_list}")

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

def parse_object_name(object_name, prefix):
    #objectName = "120_Doenjang_Jjigae_1_ingredients_5_20250414_202423.png"
    #               0       1      2   3        4    5    6       7
    #objectName = "328_Dried_Radish_Green_Set_Meal_1_ingredients_1_20250417.png"

    # Remove .png extension
    if object_name.endswith('.png') or object_name.endswith('.mp4'):
        name = object_name[:-4]
        #print(f"name: {name}")

        parts = name.split('_')
        #print(f"parts: {parts}")
    
        pos = len(parts)-1
        for i in range(len(parts)):
            #print(f"parts[{i}]: {parts[i]}")
            if parts[i].startswith('2025'):
                #print(f"parts[i]: {parts[i]}")
                pos = i
                break
        #print(f"pos: {pos}")
        # id
        id = parts[0] 
        #print(f"id: {id}")
        
        # step_image_id
        step_image_id = parts[pos-3]+'_'+parts[pos-2]+'_'+parts[pos-1] 
        #print(f"step_image_id: {step_image_id}")
            
        # create_at
        timestr = ""
        if pos == len(parts)-1:
            timestr = parts[pos]
        else:
            timestr = parts[pos]+'_'+parts[pos+1]
        #print(f"timestr: {timestr}")
        create_at = convert_timestr_to_datetime(timestr)
        #print(f"create_at: {create_at}")
        
        # image_index
        image_index = parts[pos-3]
        #print(f"image_index: {image_index}")
        
        # menu
        menu = ""
        for i in range(1, pos-3):
            # print(f"parts[i]: {parts[i]}")
            menu += parts[i]+' '
        #print(f"menu: {menu}")
        
        # s3_uri    
        s3_uri = f's3://{image_bucket_name}/{prefix}'+object_name
        #print(f"s3_uri: {s3_uri}")
        
        # step
        step = parts[pos-3]+'_'+parts[pos-2]
        #print(f"step: {step}")
        
        # Map separated parts
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
    else:
        return None

def get_url(selected_data):
    print(f"selected_data: {selected_data}")
    if selected_data is None:
        return ""
        
    s3_uri = selected_data.get('s3_uri')
    if not s3_uri:
        return ""
        
    if selected_data:
        s3_uri = selected_data.get('s3_uri')

        # Extract extension from s3_uri
        ext = s3_uri.split('.')[-1] if s3_uri else None
        print(f"ext: {ext}")

        if ext == 'mp4':
            prefix = "s3://"+video_bucket_name+"/"
            last = s3_uri.replace(prefix, '')
            prefix = "s3://"+image_bucket_name+"/"
            last = s3_uri.replace(prefix, '')
            print(f"last: {last}")
            
            url = video_cf + '/' + last
            print(f"url: {url}")
        else:
            prefix = "s3://"+image_bucket_name+"/"
            last = s3_uri.replace(prefix, '')
            print(f"last: {last}")
            
            url = image_cf + '/' + last
            print(f"url: {url}")
            
        return url
    else:
        raise Exception("selected_data is None")
        #return None

def explain_food_recommendation(persona, selected_episode, qa_pairs, food_data):
    PROMPT_rev = f"""당신은 나의 상황과 감정을 이해하고 음식을 추천하는 위트 있는 AI 큐레이터입니다.

    ### 입력 데이터:
    나의 프로필: {persona}
    선택한 에피소드: {selected_episode}
    질문과 응답: {qa_pairs}
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
    
    # return extract_json(response)
    
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

# Create a function to update DynamoDB table with the recommendation data
def update_recommendation_to_dynamodb(id, item, episode, media_list, persona, questions, recommend, recommend_id, gen_image, result):
    """
    Update the tooncraft DynamoDB table with recommendation data
    
    Args:
        id (str): Partition key
        episode (str): Selected episode
        media_list (list): List of media URLs in DynamoDB format
        persona (str): User persona description
        questions (list): List of Q&A pairs in DynamoDB format
        recommend (str): Recommendation text
        recommend_id (str): Recommendation ID
        result (str): Explanation result
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

    #FIXME
    lambda_client = boto3.client('lambda')
    result = lambda_client.invoke(
        FunctionName='toons-craft-gen-image',
        InvocationType='Event',
        Payload=json.dumps({
            "user_id": user_id,
            "device_id": device_id,
            "episode": episode,
            "image_key": f"{user_id}.jpeg"
        }, ensure_ascii=False)
    )

    # search_keyword = extract_txt_block(recommend)
    search_keyword = recommend['food_query']

    # Get embedding for user input
    user_embedding = embedding_client.embedding_text(search_keyword)

    # Search for similar foods
    similar_foods = vector_search(user_embedding, k=3)

    if similar_foods and len(similar_foods) > 0:
        recommended_food = similar_foods[0]

        food_data = recommended_food.get('_source', {}).get('metadata', {})

        print(f"Recommended food: {food_data}")
    else:
        print("No similar foods found")

    # {
    #    "img_key":"contents/762/review_illust_food.png",
    #    "review":"For 25,000 won per person, you can taste the entire sea of Tongyeong where fresh seasonal seafood meets alcohol. There's no menu, and the owner prepares fresh seafood according to the season. It's in a different class. The food keeps coming. There's no distinction between main and extra. It's a living room where you have to come back to make up if you fight while talking. It's the true face of Tongyeong.",
    #    "name":"Mulle Yasoobang",
    #    "id":"762"
    # }
    id = food_data.get('id', '')
    print(f"id: {id}")

    item = ""
    try:
        response = dynamodb.get_item(
            TableName=DYNAMO_TABLE,
            Key={'id': {'S': id}}
        )
        print(f"response: {response}")
        
        if 'Item' in response:
            # Restaurant information
            item = deserialize_dynamodb_item(response['Item'])
            print(f"Restaurant information: {item}")

            # food_data['menu'] = item.get('menu', [])

    except Exception as e:
        print(f"Error occurred while loading data: {e}")    

    item_data = {}
    ingredients = [] 
    preparation = []
    cooking = []
    plating = []
    
    for video in video_list:
        #print(f"image: {image}")
        video = video.replace(video_prefix, '')
        # print(f"video: {video}")
            
        item_data = parse_object_name(video, video_prefix)
        print(f"video item: {item_data}")
        if item_data:    
            step = item_data.get('step')
            if 'ingredients' in step and str(id) == str(item_data.get('id')):
                ingredients.append(item_data)
            if 'plating' in step and str(id) == str(item_data.get('id')):
                plating.append(item_data)
            
    print(f"ingredients: {ingredients}")
    print(f"plating: {plating}")

    for image in image_list:
        image = image.replace(image_prefix, '')
        #print(f"image: {image}")
            
        item_data = parse_object_name(image, image_prefix)
        if item_data:
            step = item_data.get('step')
            if 'preparation' in step and str(id) == str(item_data.get('id')):
                preparation.append(item_data)
            if 'cooking' in step and str(id) == str(item_data.get('id')):
                cooking.append(item_data)

    print(f"preparation: {preparation}")
    print(f"cooking: {cooking}")
    
    selected_ingredients = random.choice(ingredients) if ingredients else None
    print(f"selected_ingredients: {selected_ingredients}")

    selected_preparation = random.choice(preparation) if preparation else None
    print(f"selected_preparation: {selected_preparation}")
        
    selected_cooking = random.choice(cooking) if cooking else None
    print(f"selected_cooking: {selected_cooking}")

    selected_plating = random.choice(plating) if plating else None
    print(f"selected_plating: {selected_plating}")  

    preparation_url = get_url(selected_preparation)
    cooking_url = get_url(selected_cooking)
    plating_url = get_url(selected_plating)
    ingredients_url = get_url(selected_ingredients)

    # Ingredients - video
    # Preparation - image
    # Cooking- image
    # Plating - video
    urls = [ingredients_url, preparation_url, cooking_url, plating_url]
    print(f"urls: {urls}")

    if ingredients_url is None or preparation_url is None or cooking_url is None or plating_url is None:
        urls = default_urls

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
    
    # Update DynamoDB with the recommendation data
    episode = selected_episode
    media_list = [
        urls[0],  # ingredients video
        urls[1],  # preparation image
        urls[2],  # cooking image
        urls[3]   # plating video
    ]
    persona = persona
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
    recommend = recommend
    recommend_id = id
    
    # Check if generated image exists in S3
    gen_image_key = f"gen_image/{user_id}.jpeg"
    if check_s3_file_exists(image_bucket_name, gen_image_key):
        gen_image = f"{image_cf}/gen_image/{user_id}.jpeg"
    else:
        gen_image = ""

    result = update_recommendation_to_dynamodb(
        id=user_id,
        item=item,
        episode=episode,
        media_list=media_list,
        persona=persona,
        questions=questions,
        recommend=recommend,
        recommend_id=recommend_id,
        gen_image=gen_image,
        result=json.dumps(explaination_obj, ensure_ascii=False)
    )
    
    print(f"device_id: {device_id}")
    print(f"result: {result}")
    
    dynamodb = boto3.resource('dynamodb', region_name=REGION_NAME)
    table = dynamodb.Table('tooncraft-latest')
    response = table.put_item(Item={
        'device_id': device_id,
        'user_id': user_id,
        'id': user_id,
        'item': item,
        'episode': episode,
        'media_list': media_list,
        'persona': persona,
        'questions': questions,
        'recommend': recommend,
        'recommend_id': recommend_id,
        'gen_image': gen_image,
        'result': explaination_obj,
        'timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    })
    print(f"update latest result: {response}")

    # Invoke custom-page lambda function
    lambda_client = boto3.client('lambda')
    result = lambda_client.invoke(
        FunctionName='custom-page',
        InvocationType='Event',
        Payload=json.dumps({
            "id": user_id,
            "device_id": device_id,
            "episode": episode,
            "media_list": media_list,
            "persona": persona,
            "questions": questions,
            "recommend": recommend,
            "recommend_id": recommend_id,
            "result": explaination_obj
        }, ensure_ascii=False)
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
