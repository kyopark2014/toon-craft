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
opensearch_endpoint = 'https://search-hur-restaurants-dev-oww5qyphshcdrsh2sqizoqkdh4.aos.ap-northeast-1.on.aws'
dynamodb = boto3.client(
    'dynamodb',
    region_name=REGION_NAME,
)

image_bucket_name = 'toon-craft-gen-imgs-v2'
video_bucket_name = 'tooncraft-videos-v2'
image_prefix = 'familiar-15-menus2/'
video_prefix = 'multi_shot_automated_2/'

image_cf = 'https://d2w79zoxq32d33.cloudfront.net'
video_cf = 'https://d3dybxg1g4fwkj.cloudfront.net'

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
DYNAMO_TABLE = "hur-restaurants-500"
S3_BUCKET = "hur-restaurants-500"
S3_OUTPUT_BUCKET = "toon-craft-media"

def extract_txt_block(text):
    pattern = r"```txt(.*?)```"
    match = re.search(pattern, text, re.DOTALL)
    
    if match:
        return match.group(1).strip()
    return ""

def deserialize_dynamodb_item(item):
    """DynamoDB 항목을 파이썬 딕셔너리로 변환"""
    return {k: TypeDeserializer().deserialize(v) for k, v in item.items()}

def get_image_url(path):
    """이미지 경로를 CloudFront URL로 변환"""
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

    # .png 확장자 제거
    if object_name.endswith('.png') or object_name.endswith('.mp4'):
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
        s3_uri = f's3://{image_bucket_name}/{prefix}'+object_name
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
    else:
        return None

def get_url(selected_data):
    s3_uri = selected_data.get('s3_uri')

    # s3_uri에서 확장자 추출
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

def explain_food_recommendation(persona, selected_episode, qa_pairs, food_data):
    """음식 추천에 대한 설명을 생성합니다."""
    PROMPT = f"""당신은 나의 상황과 감정을 이해하고 음식을 추천하는 공감적인 AI 음식 큐레이터입니다.

    ### 입력 데이터:
    나의 프로필: {persona}
    선택한 에피소드: {selected_episode}
    질문과 응답: {qa_pairs}
    추천된 음식: {food_data.get('menu', '')}
    식당 이름: {food_data.get('name', '')}
    식당 음식의 허영만 선생님 의견: {food_data.get('review', '')}

    ### 당신의 임무:
    1. 추천된 음식이 나의 현재 상황과 어떻게 잘 맞는지 설명하세요.
    2. 이 음식이 나의 기분이나 컨디션을 어떻게 개선할 수 있는지 설명하세요.
    3. 허영만 선생님의 리뷰를 참조하여 음식의 특징과 매력적인 점을 설명하세요.
    4. 공감적이고 따뜻한 톤으로 설명하되, 이모지를 적절히 활용하여 친근하게 작성하세요.

    ### 출력:
    나의 상황에 맞춘 음식 추천 설명을 작성하세요.
    """

    claude = BedrockClaude(region='us-east-1', modelId=BedrockModel.SONNET_3_7_CR)
    # for chunk in claude.converse_stream(text=PROMPT):
    #     yield chunk
    return claude.converse(text=PROMPT)

def lambda_handler(event, context):
    user_id = event.get('user_id', '')
    recommend = event.get('recommend', '')
    persona = event.get('persona', '')
    selected_episode = event.get('selected_episode', '')
    qa_pairs = event.get('qa_pairs', '')

    # recommend = """
    # #### 오늘의 당신은?
    # - **현재 감정**: 성취감, 열정, 기쁨
    # - **상황**: 동료들과의 토론에서 아이디어가 채택되어 성공적인 순간을 경험함
    # #### 추천 음식
    # ```txt
    # 과학적 호기심과 예술적 감성이 공존하는 당신에게, 성취의 기쁨을 더욱 풍성하게 해줄 색감이 화려하고 다양한 맛의 조화가 돋보이는 한식 요리
    # ```
    # #### 추천 이유
    # 오늘 당신은 마치 완벽한 커피 한 잔처럼 균형 잡힌 하루를 보내셨군요! 과학 기술에 대한 열정과 예술적 감성을 모두 갖춘 당신의 아이디어가 빛을 발한 특별한 날이니, 그 성취감을 더욱 풍성하게 해줄 음식이 필요합니다.
    # 마치 다양한 커피를 음미하듯 여러 맛이 조화롭게 어우러진 한식이 어떨까요? 색감이 화려한 음식은 당신의 예술적 감성을 만족시키고, 다채로운 맛의 조합은 과학적 호기심을 자극할 거예요. 성공의 짜릿함을 입안 가득 느끼며, 오늘의 기쁨을 더욱 특별하게 기념해보세요. 당신의 빛나는 아이디어처럼, 오늘 저녁도 빛나길 바랍니다!
    # """

    search_keyword = extract_txt_block(recommend)

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
    #    "review":"1인당 25,000원을 투자하면 통영의 바다를 통째로 맛볼 수 있는 제철 해산물과 술이 만나는 곳. 메뉴는 따로 없고 주인이 제철에 맞춰 싱싱한 해산물을 그때그때 준비해 내준다. 클래스가 다르다. 계속 나오는 음식. 메인과 엑스트라가 따로 없다. 얘기 나누다가 싸우면 화해하기 위해 또 와야 하는 사랑방이다. 통영의 진면목이다.",
    #    "name":"물레야소주방",
    #    "id":"762"
    # }

    item = url2 = url3 = ""
    try:
        response = dynamodb.get_item(
            TableName=DYNAMO_TABLE,
            Key={'id': {'S': food_data.get('id', '')}}
        )
        print(f"response: {response}")
        
        if 'Item' in response:
            # 식당 정보
            item = deserialize_dynamodb_item(response['Item'])
            print(f"식당 정보: {item}")

            # food_data['menu'] = item.get('menu', [])

            # 음식 사진
            url2 = get_image_url(item.get('media', {}).get('photos')[2])
            print(f"음식 사진2: {url2}")
            url3 = get_image_url(item.get('media', {}).get('photos')[3])
            print(f"음식 사진3: {url3}")

    except Exception as e:
        print(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")

    image_list = get_s3_list(image_bucket_name, prefix=image_prefix)
    print(f"image_list: {image_list}")

    video_list = get_s3_list(video_bucket_name, prefix=video_prefix)
    print(f"video_list: {video_list}")

    item_data = {}
    ingredients = [] 
    preparation = []
    cooking = []
    plating = []
    id = "120"

    for video in video_list:
        #print(f"image: {image}")
        video = video.replace(video_prefix, '')
        print(f"video: {video}")
            
        item_data = parse_object_name(video, video_prefix)    
        if item_data:    
            step = item_data.get('step')
            if 'ingredients' in step and id == item_data.get('id'):
                ingredients.append(item_data)
            if 'plating' in step and id == item_data.get('id'):
                plating.append(item_data)
            
        print(f"ingredients: {ingredients}")
        print(f"plating: {plating}")

        for image in image_list:
            #print(f"image: {image}")
            image = image.replace(image_prefix, '')
            print(f"image: {image}")
                
            item_data = parse_object_name(image, image_prefix)
            if item_data:
                step = item_data.get('step')
                if 'preparation' in step and id == item_data.get('id'):
                    preparation.append(item_data)
                if 'cooking' in step and id == item_data.get('id'):
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

    explaination = explain_food_recommendation(persona, selected_episode, qa_pairs, food_data)
    print(f"explaination: {explaination}")
    info = {
        "img_key": food_data.get('img_key', ''),
        "review": food_data.get('review', ''),
        "name": food_data.get('name', ''),
        "id": food_data.get('id', ''),
        "item": item,
        "urls": json.dumps(urls, ensure_ascii=False),
        "explaination": explaination
    }    
    print(f"info: {info}")
    
    result = {
        "user_id": user_id,
        "info": info
    }

    return {
        'statusCode': 200,
        'body': json.dumps(result, ensure_ascii=False)
    }
