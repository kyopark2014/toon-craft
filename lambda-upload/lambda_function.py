import boto3
import json
from genai_kit.aws.amazon_image import BedrockAmazonImage, ImageParams, NovaImageSize
from genai_kit.aws.bedrock import BedrockModel
from genai_kit.aws.claude import BedrockClaude

canvas = BedrockAmazonImage(modelId=BedrockModel.NOVA_CANVAS)

REGION_NAME = "ap-northeast-1"
CF_DOMAIN = "https://d1z4gor1v1vm43.cloudfront.net"
DYNAMO_TABLE = "hur-restaurants-500"
S3_BUCKET = "hur-restaurants-500"
S3_OUTPUT_BUCKET = "toon-craft-media"

boto3.setup_default_session()

def extract_json(str):
    try:
        str = str.replace('```json', '').replace('```', '')
        return json.loads(str)
    except Exception as e:
        print(f"Error: {str}")
        return {}

def generate_persona_and_questions(image_bytes):
    PROMPT = """너는 내 얼굴에서 분위기와 성격을 추론하는 감성적인 AI 스토리텔러야. 일상을 기반으로 스토리를 만들 거야.

    <instruction>
    1. 이미지에서 인물의 성별, 나이대, 인상, 성격 등을 분석하세요
    2. 인물에 대한 정보를 토대로 이 인물의 페르소나를 정의하세요. 성격이나 직업적 특성을 반영하세요.
    3. 추론된 성별, 나이대, 성격, 직업을 토대로 유쾌하거나 재밌있는 에피소드에 대해 세 가지 정의하세요. 최신 트렌드를 반영하고 이모지를 사용하여 유쾌하게 작성하세요.
    </instruction>

    아래와 같은 json 포맷으로 답변하세요. 항상 한글로 서술하세요:
    - persona: str (성별, 나이대, 인상, 성격, 직업에 대해 1-2줄로 서술)
    - episode: list[str]
    """

    claude = BedrockClaude(region='us-east-1', modelId=BedrockModel.NOVA_LITE_CR)
    story_starter = claude.converse(text=PROMPT, image=image_bytes, format='jpeg')
    story_starter = extract_json(story_starter)

    persona = story_starter.get('persona', '')
    episode = story_starter.get('episode', [])
    
    # Return without generating questions yet
    return persona, episode

bucketName = "toon-craft-gen-imgs-v2"
folderName = "upload_image"
    
def lambda_handler(event, context):
    user_id = event['user_id']  
    image_key = event['image_key']
    
    #image_key = "ksdyb-high-res-current-photo.jpeg"

    # S3 클라이언트 생성
    s3_client = boto3.client('s3')

    # 이미지 파일 경로 생성
    image_path = f"{folderName}/{image_key}"

    # S3에서 이미지 데이터 읽기
    response = s3_client.get_object(Bucket=bucketName, Key=image_path)
    img_data = response['Body'].read()

    # 이미지 데이터를 바이트 배열로 변환
    img_bytes = bytes(img_data)

    persona, episode = generate_persona_and_questions(img_bytes)

    print(f"persona: {persona}")
    print(f"episode: {episode}")
    
    result = {
        "user_id": user_id,
        "persona": persona,
        "episode": episode
    }

    return {
        'statusCode': 200,
        'body': json.dumps(result, ensure_ascii=False)
    }
