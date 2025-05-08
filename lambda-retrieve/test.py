import boto3
import json
import re
from genai_kit.aws.amazon_image import BedrockAmazonImage, ImageParams, NovaImageSize
from genai_kit.aws.bedrock import BedrockModel
from genai_kit.aws.claude import BedrockClaude
from genai_kit.aws.embedding import BedrockEmbedding
from opensearchpy import OpenSearch, RequestsHttpConnection
from boto3.dynamodb.types import TypeDeserializer
import random

image_bucket_name = 'toon-craft-gen-imgs-v2'
video_bucket_name = 'tooncraft-videos-v2'
image_prefix = 'familiar-15-menus2/'
video_prefix = 'multi_shot_automated_2/'

image_cf = 'https://d2w79zoxq32d33.cloudfront.net'
video_cf = 'https://d3dybxg1g4fwkj.cloudfront.net'

viewer = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>이미지와 비디오 갤러리</title>
    <style>
        body {{
            background-color: #F0F0F0;
            background-image: url('https://d2w79zoxq32d33.cloudfront.net/html/background.jpg');
            background-size: cover;
            background-position: center;
            background-repeat: no-repeat;
            min-height: 100vh;
            margin: 0;
        }}
        .gallery {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 0;
            padding: 0;
            max-width: 100%;
            margin: 0;
            height: calc(100vh - 300px);
            align-items: center;
        }}
        .gallery-item {{
            width: 100%;
            height: calc((100vh - 300px) / 2);
            object-fit: cover;
            border: 8px solid #000;
            box-shadow: 8px 8px 0 #000;
            transition: transform 0.3s ease;
            background-color: #fff;
            position: relative;
            overflow: hidden;
            margin: 4px;
        }}
        .gallery-item::before {{
            content: '';
            position: absolute;
            top: -4px;
            left: -4px;
            right: -4px;
            bottom: -4px;
            border: 2px solid #000;
            z-index: 1;
            pointer-events: none;
        }}
        .gallery-item::after {{
            content: '';
            position: absolute;
            top: 4px;
            left: 4px;
            right: 4px;
            bottom: 4px;
            border: 2px solid #000;
            z-index: 1;
            pointer-events: none;
        }}
        .gallery-item:hover {{
            transform: scale(1.02);
        }}
        .gallery-item video {{
            width: 100%;
            height: 100%;
            object-fit: cover;
            position: absolute;
            top: 0;
            left: 0;
            transform: none;
        }}
        .text-content {{
            position: relative;
            background-color: rgba(255, 255, 255, 0.9);
            padding: 20px;
            font-family: 'Noto Sans KR', sans-serif;
            line-height: 1.6;
            margin-top: 20px;
            height: 300px;
            overflow-y: auto;
            border: 2px solid #000;
            box-shadow: 4px 4px 0 #000;
        }}
        /* 스크롤바 스타일링 */
        .text-content::-webkit-scrollbar {{
            width: 8px;
        }}
        .text-content::-webkit-scrollbar-track {{
            background: #F1F1F1;
        }}
        .text-content::-webkit-scrollbar-thumb {{
            background: #888;
            border-radius: 4px;
        }}
        .text-content::-webkit-scrollbar-thumb:hover {{
            background: #555;
        }}
        /* 기존 스크롤 애니메이션 제거 */
        @keyframes scrollText {{
            0% {{
                transform: none;
            }}
            100% {{
                transform: none;
            }}
        }}
        .text-content:hover {{
            animation-play-state: paused;
        }}
        .text-content h4 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .text-content ul {{
            margin: 0;
            padding-left: 20px;
        }}
        .text-content pre {{
            background-color: #F5F5F5;
            padding: 10px;
            border-radius: 5px;
            margin: 10px 0;
        }}
    </style>
</head>
<body>
    <div class="gallery">
        <video class="gallery-item" controls loop autoplay muted>
            <source src="{url1}" type="video/mp4">
            브라우저가 비디오를 지원하지 않습니다.
        </video>
        <img class="gallery-item" src="{url2}" alt="조리 이미지">
        <img class="gallery-item" src="{url3}" alt="플레이팅 이미지">
        <video class="gallery-item" controls loop autoplay muted>
            <source src="{url4}" type="video/mp4">
            브라우저가 비디오를 지원하지 않습니다.
        </video>
    </div>
    <div class="text-content">
        {text}
    </div>
</body>
</html>
"""
def generate_html(url1, url2, url3, url4, text):
    return viewer.format(url1=url1, url2=url2, url3=url3, url4=url4, text=text)

canvas = BedrockAmazonImage(modelId=BedrockModel.NOVA_CANVAS)
REGION_NAME = "ap-northeast-1"
opensearch_index = 'hur-resto'
opensearch_endpoint = 'https://search-hur-restaurants-dev-oww5qyphshcdrsh2sqizoqkdh4.aos.ap-northeast-1.on.aws'
dynamodb = boto3.client(
    'dynamodb',
    region_name=REGION_NAME,
)

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

recommend = """
#### Today's you?
- **Current emotion**: Achievement, enthusiasm, joy
- **Situation**: Experiencing a successful moment after participating in a discussion with colleagues about a new idea that was accepted
#### Recommended food
```txt
A dish that combines scientific curiosity and artistic sensibility, suitable for you who have both
```
#### Why recommend this
You must have felt the success of today! You have both enthusiasm for science and artistic sensibility, so you need a dish that can further enhance your achievement. How about a dish that harmonizes various flavors and colors, which can satisfy your artistic sensibility and stimulate your scientific curiosity? Let's celebrate today's joy even more!
"""
print(f"recommend: {recommend}")

request = {
    "user_id": "1234567890",
    "recommend": recommend
}
print(f"request: {request}")

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
        # url2 = get_image_url(item.get('media', {}).get('photos')[2])
        # print(f"음식 사진2: {url2}")
        # url3 = get_image_url(item.get('media', {}).get('photos')[3])
        # print(f"음식 사진3: {url3}")

except Exception as e:
    print(f"데이터를 불러오는 중 오류가 발생했습니다: {e}")

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

    ### Input data:
    My profile: {persona}
    Selected episode: {selected_episode}
    Questions and answers: {qa_pairs}
    Recommended food: {food_data.get('menu', '')}
    Restaurant name: {food_data.get('name', '')}
    Hyeongman Seon's opinion on the restaurant's food: {food_data.get('review', '')}

    ### Your mission:
    1. Explain how this food matches your current situation.
    2. Explain how this food can improve your mood or condition.
    3. Based on Hyeongman Seon's review, explain the features and attractive points of the food.
    4. Explain in a warm and empathetic tone, using appropriate emojis to make it friendly.

    ### Output:
    Please write an explanation of food recommendation tailored to your situation.
    """

    claude = BedrockClaude(region='us-east-1', modelId=BedrockModel.SONNET_3_7_CR)
    # for chunk in claude.converse_stream(text=PROMPT):
    #     yield chunk
    return claude.converse(text=PROMPT)


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

import random
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

persona = "This person is in their late 30s and appears to be male. They wear glasses and have an intellectual image, and it seems they have a cheerful and lively personality. They may have a job related to academic fields."
selected_episode = "On a day when they were discussing a new idea with colleagues while drinking coffee, they had a heated discussion about the idea. He explained his idea and was enthusiastic about it, and eventually his idea was accepted.",
qa_pairs = [
   {
      "question":"When thinking about the discussion with colleagues about the idea you liked the most, what was it?",
      "answer": "Science and technology related topics"
   },
   {
      "question":"When discussing the idea with colleagues and being enthusiastic about it, what activity do you like to express your thoughts?",
      "answer": "Expressing thoughts through artistic expressions, for example, drawing or music"
   },
   {
      "question":"What is the person most likely to enjoy as a hobby? Please choose one from below.",
      "answer": "Drinking various drinks at a coffee shop"
   }
]

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

html = generate_html(urls[0], urls[1], urls[2], urls[3], explaination)
print(f"html: {html}")
# S3에 HTML 파일 업로드
s3_client = boto3.client('s3')
try:
    s3_client.put_object(
        Bucket=image_bucket_name,
        Key='html/viewer.html',
        Body=html,
        ContentType='text/html'
    )
    print("HTML 파일이 성공적으로 업로드되었습니다.")
except Exception as e:
    print(f"HTML 파일 업로드 중 오류 발생: {e}")


id = id
episode = selected_episode

media_list = [
    {"S": urls[0]},  # ingredients video
    {"S": urls[1]},  # preparation image
    {"S": urls[2]},  # cooking image
    {"S": urls[3]}   # plating video
]
persona = persona

questions = [
    {
        "M": {
            "question": {"S": qa_pairs[0]["question"]},
            "answer": {"S": qa_pairs[0]["answer"]}
        }
    },
    {
        "M": {
            "question": {"S": qa_pairs[1]["question"]},
            "answer": {"S": qa_pairs[1]["answer"]}
        }
    },
    {
        "M": {
            "question": {"S": qa_pairs[2]["question"]},
            "answer": {"S": qa_pairs[2]["answer"]}
        }
    }
]

recommend = recommend

recommend_id = id

result = explaination

# Create a function to update DynamoDB table with the recommendation data
def update_recommendation_to_dynamodb(id, episode, media_list, persona, questions, recommend, recommend_id, result):
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
        dynamodb = boto3.client('dynamodb', region_name=REGION_NAME)
        
        # Prepare the item for DynamoDB
        item = {
            'id': {'S': id},  # Partition key
            'episode': {'S': episode},
            'media_list': {'L': media_list},  # List type
            'persona': {'S': persona},
            'questions': {'L': questions},  # List type
            'recommend': {'S': recommend},
            'recommend_id': {'S': recommend_id},
            'result': {'S': result}
        }
        
        # Put item into DynamoDB
        response = dynamodb.put_item(
            TableName='tooncraft',
            Item=item
        )
        
        print("Successfully updated recommendation in DynamoDB")
        return response
        
    except Exception as e:
        print(f"Error updating DynamoDB: {str(e)}")
        raise e

# Update DynamoDB with the recommendation data
result = update_recommendation_to_dynamodb(
    id=id,
    episode=episode,
    media_list=media_list,
    persona=persona,
    questions=questions,
    recommend=recommend,
    recommend_id=recommend_id,
    result=result
)
print(f"result: {result}")

# Invoke custom-page lambda function
lambda_client = boto3.client('lambda')
result = lambda_client.invoke(
    FunctionName='custom-page.lambda',
    InvocationType='Event',
    Payload=json.dumps({
        "id": id,
        "episode": episode,
        "media_list": media_list,
        "persona": persona,
        "questions": questions,
        "recommend": recommend,
        "recommend_id": recommend_id,
        "result": explaination
    })
)
print(f"result: {result}")
    



