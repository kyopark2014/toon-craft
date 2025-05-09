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
video_prefix = 'multi_shot_automated_2/'

image_cf = 'https://d2w79zoxq32d33.cloudfront.net'
video_cf = 'https://d3dybxg1g4fwkj.cloudfront.net'

default_urls = [
        "https://d3dybxg1g4fwkj.cloudfront.net/multi_shot_automated_2/120_Doenjang_Jjigae_1_ingredients_5_20250414_202423_20250506_114301/dygsdxd00vro/shot_0004.mp4",
        "https://d2w79zoxq32d33.cloudfront.net/familiar-15-menus2/120_Doenjang_Jjigae_2_preparation_4_20250414_202518.png",
        "https://d2w79zoxq32d33.cloudfront.net/familiar-15-menus2/120_Doenjang_Jjigae_3_cooking_4_20250414_202623.png",
        "https://d3dybxg1g4fwkj.cloudfront.net/multi_shot_automated_2/120_Doenjang_Jjigae_4_plating_3_20250414_202723_20250506_115350/qpnyuhqrjhwh/shot_0002.mp4"
    ]

viewer = """
<!DOCTYPE html>
<html lang="ko">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Image and Video Gallery</title>
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
        /* Scrollbar styling */
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
        /* Remove existing scroll animation */
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
            Your browser does not support video.
        </video>
        <img class="gallery-item" src="{url2}" alt="Cooking image">
        <img class="gallery-item" src="{url3}" alt="Plating image">
        <video class="gallery-item" controls loop autoplay muted>
            <source src="{url4}" type="video/mp4">
            Your browser does not support video.
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
    """Generate explanation for food recommendation."""
    PROMPT = f"""You are an empathetic AI food curator who understands my situation and emotions to recommend food.

    ### Input Data:
    My Profile: {persona}
    Selected Episode: {selected_episode}
    Questions and Answers: {qa_pairs}
    Recommended Food: {food_data.get('menu', '')}
    Restaurant Name: {food_data.get('name', '')}
    Chef Heo Young-man's Opinion: {food_data.get('review', '')}

    ### Your Task:
    1. Explain how the recommended food matches my current situation.
    2. Explain how this food can improve my mood or condition.
    3. Explain the characteristics and appealing points of the food with reference to Chef Heo's review.
    4. Write in an empathetic and warm tone, using appropriate emojis to make it friendly.

    ### Output:
    Write a food recommendation explanation tailored to my situation.
    """

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

def lambda_handler(event, context):
    user_id = event.get('user_id', '')
    recommend = event.get('recommend', '')
    persona = event.get('persona', '')
    selected_episode = event.get('selected_episode', '')
    qa_pairs = event.get('qa_pairs', '')

    # recommend = """
    # #### Today's You
    # - **Current Emotion**: Sense of achievement, passion, joy
    # - **Situation**: Experienced a successful moment when your idea was adopted in a discussion with colleagues
    # #### Recommended Food
    # ```txt
    # A Korean dish with vibrant colors and harmonious flavors that will enrich your sense of achievement, perfect for someone with both scientific curiosity and artistic sensibility
    # ```
    # #### Reason for Recommendation
    # Today, you've had a perfectly balanced day like a perfect cup of coffee! It's a special day when your idea, combining both passion for science and technology and artistic sensibility, shone brightly. You need food that will make that sense of achievement even more fulfilling.
    # How about a Korean dish with harmonious flavors, just like savoring different types of coffee? The vibrant colors will satisfy your artistic sensibility, and the diverse flavor combinations will stimulate your scientific curiosity. Feel the thrill of success in your mouth, and make today's joy even more special. May your evening shine as brightly as your brilliant idea!
    # """

    # search_keyword = extract_txt_block(recommend)
    search_keyword = recommend["food_query"]

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
        if item_data:    
            step = item_data.get('step')
            if 'ingredients' in step and id == item_data.get('id'):
                ingredients.append(item_data)
            if 'plating' in step and id == item_data.get('id'):
                plating.append(item_data)
            
    print(f"ingredients: {ingredients}")
    print(f"plating: {plating}")

    for image in image_list:
        image = image.replace(image_prefix, '')
        #print(f"image: {image}")
            
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
    
    # Create formatted HTML content from the explanation object
    recommendation = explaination_obj.get('recommendation_result', {})
    html_content = f"""
        <h2>{recommendation.get('title', '')}</h2>
        <p>{recommendation.get('description', '')}</p>
        <h3>추천 이유</h3>
        <p>1. {recommendation.get('reason_1', '')}</p>
        <p>2. {recommendation.get('reason_2', '')}</p>
        <p>3. {recommendation.get('reason_3', '')}</p>
    """
    html = generate_html(urls[0], urls[1], urls[2], urls[3], html_content)
    print(f"html: {html}")
    # Upload HTML file to S3
    s3_client = boto3.client('s3')
    try:
        s3_client.put_object(
            Bucket=image_bucket_name,
            Key='html/viewer.html',
            Body=html,
            ContentType='text/html'
        )
        print("HTML file successfully uploaded.")
    except Exception as e:
        print(f"Error occurred while uploading HTML file: {e}")

    # Update DynamoDB with the recommendation data
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

    result = update_recommendation_to_dynamodb(
        id=user_id,
        episode=episode,
        media_list=media_list,
        persona=persona,
        questions=questions,
        recommend=recommend,
        recommend_id=recommend_id,
        result=json.dumps(explaination_obj, ensure_ascii=False)
    )
    print(f"result: {result}")

    # Invoke custom-page lambda function
    lambda_client = boto3.client('lambda')
    result = lambda_client.invoke(
        FunctionName='custom-page',
        InvocationType='Event',
        Payload=json.dumps({
            "id": user_id,
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
            "info": info
        }
    }
