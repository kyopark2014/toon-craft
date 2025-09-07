import boto3
import json
import base64
import uuid
import time
import random
import secrets
from botocore.exceptions import ClientError
from genai_kit.aws.amazon_image import BedrockAmazonImage, ImageParams, NovaImageSize
from genai_kit.aws.bedrock import BedrockModel
from genai_kit.aws.claude import BedrockClaude

canvas = BedrockAmazonImage(modelId=BedrockModel.NOVA_CANVAS)


# AWS 리소스 설정
REGION_NAME = "us-east-1"
MODEL_ID = "amazon.nova-canvas-v1:0"

CF_DOMAIN = "https://d2w79zoxq32d33.cloudfront.net"
S3_BUCKET = "toon-craft-gen-imgs-v2"
S3_BUCKET_INPUT_FOLDER = "upload_image"
S3_BUCKET_OUTPUT_FOLDER = "gen_image"


def generate_image_prompt(image_bytes, episode):
    PROMPT = f"""당신은 이미지 생성 모델의 프롬프트를 생성하는 프롬프트 엔지니어 입니다.
    주어진 이미지에서 대표적인 한 명의 인물이 아래와 같은 상황에 있는 이미지를 생성하려고 합니다.
    인물의 얼굴 특징을 최대한 그대로 유지하면서, 인물이 젊고 활기차고 매력적으로 표현되도록 하세요.
    에피소드 상황을 중심으로 하지만, 전반적으로 따뜻하고 긍정적인 에너지와 시각적으로 매력적인 스타일을 부여하세요.
    
    - episode: {episode}

    출력 형식은 별도 설명 없이 다음 형식의 JSON으로 응답하세요:
    {{
        "prompt": "영문 한 문장으로 이미지 생성 프롬프트를 800자 이내로 작성하세요. 이모지는 제거하세요"
    }}
    """

    try:
        claude = BedrockClaude(region='us-east-1', modelId=BedrockModel.NOVA_PRO_CR)
        response = claude.converse(text=PROMPT, image=image_bytes, format='jpeg')
        print(f"LLM response: {response}")
    
        # Find JSON content between curly braces
        start = response.find('{')
        end = response.rfind('}') + 1
        if start != -1 and end != 0:
            json_str = response[start:end]
            # Parse and return only the JSON part
            return json.loads(json_str)
        return {"prompt": "smiling face"}
    except:
        return { "prompt": "smiling face" }

def generate_image(image_bytes, prompt):
    width = 1280
    height = 720
    cfgScale = 9.0
    similarity = 0.8
    seed = 512
    # seed = secrets.randbelow(2147483647)
    
    # Convert bytes to base64 string
    image_base64 = base64.b64encode(image_bytes).decode('utf-8')
    
    body = json.dumps({
        "taskType": "IMAGE_VARIATION",
        "imageVariationParams": {
            "images": [image_base64],
            "similarityStrength": similarity,
            "text": f"{prompt}, asian, beautiful, cartoon style, colorful digital sketch",
            "negativeText": "text, ugly, old, aged, deformed, low quality, blurry"
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
                          region_name=REGION_NAME)
    
    response = bedrock.invoke_model(
        body=body,
        modelId=MODEL_ID,
        accept="application/json",
        contentType="application/json"
    )
    response_body = json.loads(response.get("body").read())
    image = response_body.get("images")[0]
    return image

def generate_image_with_retry(image_bytes, episode):
    max_retries = 3
    initial_delay = 1
    
    for attempt in range(max_retries):
        try:
            image_prompt = generate_image_prompt(image_bytes, episode).get('prompt', 'smiling face')
            print(f"image_prompt: {image_prompt}")
            
            img = generate_image(image_bytes, image_prompt)
            print('generate success!')
            return img, image_prompt
            
        except Exception as e:
            if attempt == max_retries - 1:
                print(f"Failed after {max_retries} attempts. Last error: {str(e)}")
                raise
            
            delay = initial_delay * (2 ** attempt)
            print(f"Attempt {attempt + 1} failed. Retrying in {delay} seconds... Error: {str(e)}")
            time.sleep(delay)
    
    
def lambda_handler(event, context):
    try:
        # Parse body if it's a string
        if isinstance(event.get('body'), str):
            body = json.loads(event['body'])
        else:
            body = event.get('body', event)
        
        # Extract values from body
        try:
            user_id = body['user_id']
            episode = body['episode']
            device_id = body.get('device_id', '1')
            image_key = body['image_key']
        except KeyError as e:
            print(f"Missing required field: {str(e)}")
            return {
                'statusCode': 400,
                'body': json.dumps({'error': f'Missing required field: {str(e)}'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # S3 클라이언트 생성
        s3_client = boto3.client('s3')

        try:
            # S3에서 이미지 데이터 읽기
            response = s3_client.get_object(
                Bucket=S3_BUCKET,
                Key=f"{S3_BUCKET_INPUT_FOLDER}/{image_key}"
            )
            img_data = response['Body'].read()
        except Exception as e:
            print(f"Error reading from S3: {str(e)}")
            return {
                'statusCode': 404,
                'body': json.dumps({'error': 'Image not found in S3'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }

        # 이미지 데이터를 바이트 배열로 변환
        img_bytes = bytes(img_data)
        
        try:
            img, image_prompt = generate_image_with_retry(img_bytes, episode)
            
            # Convert base64 to bytes
            img_bytes = base64.b64decode(img)
        except Exception as e:
            print(f"Error generating image: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to generate image'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        try:
            # Generate unique filename
            output_key = f"{S3_BUCKET_OUTPUT_FOLDER}/{user_id}.jpeg"
            
            # Upload to S3
            s3_client.put_object(
                Bucket=S3_BUCKET,
                Key=output_key,
                Body=img_bytes,
                ContentType='image/jpeg'
            )
            
            print('output_key', output_key)
        except Exception as e:
            print(f"Error uploading to S3: {str(e)}")
            return {
                'statusCode': 500,
                'body': json.dumps({'error': 'Failed to upload generated image'}),
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                }
            }
        
        # Generate CloudFront URL
        cf_url = f"{CF_DOMAIN}/{output_key}"
        
        result = {
            "user_id": user_id,
            "device_id": device_id,
            "image_prompt": image_prompt,
            "img": cf_url,
        }
        
        print('result: ', json.dumps(result))

        return {
            'statusCode': 200,
            'body': json.dumps(result),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        return {
            'statusCode': 500,
            'body': json.dumps({'error': 'Internal server error'}),
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            }
        }

