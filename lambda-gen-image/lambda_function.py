import boto3
import json
import base64
import uuid
from genai_kit.aws.amazon_image import BedrockAmazonImage, ImageParams, NovaImageSize
from genai_kit.aws.bedrock import BedrockModel
from genai_kit.aws.claude import BedrockClaude

canvas = BedrockAmazonImage(modelId=BedrockModel.NOVA_CANVAS)


# AWS 리소스 설정
REGION_NAME = "us-east-1"
MODEL_ID = "amazon.nova-canvas-v1:0"

CF_DOMAIN = "https://d1z4gor1v1vm43.cloudfront.net"
S3_BUCKET = "toon-craft-gen-imgs-v2"
S3_BUCKET_INPUT_FOLDER = "upload_image"
S3_BUCKET_OUTPUT_FOLDER = "gen_image"


def generate_image_prompt(image_bytes, episode):
    PROMPT = f"""당신은 이미지 생성 모델의 프롬프트를 생성하는 프롬프트 엔지니어 입니다.
    주어진 이미지에서 대표적인 한 명의 인물이 아래와 같은 상황에 있는 이미지를 생성하려고 합니다.
    에피소드를 강조하도록 이미지 프롬프트를 생성해주세요.

    - episode: {episode}

    출력 형식은 아래를 따르세요:
    {{
        "prompt": "영문 한 문장으로 이미지 생성 프롬프트. 이모지는 제거하세요"
    }}
    """

    claude = BedrockClaude(region='us-east-1', modelId=BedrockModel.SONNET_3_7_CR)
    res = claude.converse(text=PROMPT, image=image_bytes, format='jpeg')
    prompt = json.loads(res).get('prompt', 'smiling face')
    return prompt


def generate_image(image_bytes, prompt):
    width = 1280
    height = 720
    seed = 512
    cfgScale = 9.0
    similarity = 0.8
    
    body = json.dumps({
        "taskType": "IMAGE_VARIATION",
        "imageVariationParams": {
            "images": [image_bytes],
            "similarityStrength": similarity,
            "text": f"{prompt}, asian, cartoon style, colorful digital illustration",
            "negativeText": "ugly, deformed, low quality, blurry"
        },
        "imageGenerationConfig": {
            "numberOfImages": 1,
            "width": width,
            "height": height,
            "cfgScale": cfgScale,
            "seed": seed
        }
    })
    
    bedrock = boto3.client(service_name='bedrock-runtime',
                           region_name = REGION_NAME)
    response = bedrock.invoke_model(
        body=body,
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json"
    )
    response_body = json.loads(response.get("body").read())
    image = response_body.get("images")[0]
    return image
    
    
def lambda_handler(event, context):
    user_id = event['user_id']
    persona = event['persona']
    device_id = event.get('device_id', '1')
    image_key = event['image_key']
    
    # S3 클라이언트 생성
    s3_client = boto3.client('s3')

    # S3에서 이미지 데이터 읽기
    response = s3_client.get_object(
        Bucket=S3_BUCKET,
        Key=f"{S3_BUCKET_INPUT_FOLDER}/{image_key}"
    )
    img_data = response['Body'].read()

    # 이미지 데이터를 바이트 배열로 변환
    img_bytes = bytes(img_data)
    
    image_prompt = generate_image_prompt(img_bytes, persona)
    print(f"image_prompt: {image_prompt}")
    
    img = generate_image(img_bytes, image_prompt)
    
    # Convert base64 to bytes
    img_bytes = base64.b64decode(img)
    
    # Generate unique filename
    output_key = f"{S3_BUCKET_OUTPUT_FOLDER}/{user_id}.jpeg"
    
    # Upload to S3
    s3_client.put_object(
        Bucket=S3_BUCKET,
        Key=output_key,
        Body=img_bytes,
        ContentType='image/jpeg'
    )
    
    # Generate CloudFront URL
    cf_url = f"{CF_DOMAIN}/{output_key}"
    
    result = {
        "user_id": user_id,
        "image_prompt": image_prompt,
        "img": cf_url,
    }

    return {
        'statusCode': 200,
        'body': result
    }
