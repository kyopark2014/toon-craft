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

def generate_recommendation(persona, selected_episode, qa_pairs):
    PROMPT = f"""당신은 나의 하루와 정서적 상태를 고려하여 음식을 추천하는 AI 한식 음식 큐레이터입니다.
    나의 설문 응답을 분석하여 그날의 기분과 상황에 딱 맞는 음식을 추천하기 위한 검색 쿼리를 생성해야 합니다.

    ### 입력 데이터:
    나의 프로필: {persona}
    선택한 에피소드: {selected_episode}
    질문과 응답: {qa_pairs}

    ### 출력: 아래와 같은 마크다운 형식을 사용하세요:
    
    #### 오늘의 당신은?
    입력된 정보를 분석하여 다음을 파악하세요:

    - **현재 감정**: 나의 현재 감정 상태 (기쁨, 슬픔, 스트레스, 지침, 설렘 등)
    - **상황**: 오늘 하루의 특별한 상황이나 이벤트

    #### 추천 음식

    ```txt
    나에게 추천할 만한 개인화된 검색 문장을 한 문장으로 작성하세요. 특정 음식을 언급하지 마세요.
    - 나의 현재 감정 상태에 도움이 될 수 있는 음식의 특성
    - 나의 하루를 더 나아지게 할 수 있는 음식 요소
    - 나의 상황과 연결된 음식의 정서적 가치
    - 음식의 분위기나 경험적 측면 (위로, 응원, 활력, 안정감 등)
    ```

    #### 추천 이유

    (재미있고 공감가는 표현을 사용하여 추천하는 이유를 서술하세요)
    """

    PROMPT_rev = f"""당신은 나의 하루와 정서적 상태를 고려하여 음식을 추천하는 AI 한식 음식 큐레이터입니다.
    나의 설문 응답을 분석하여 그날의 기분과 상황에 딱 맞는 음식을 추천하기 위한 검색 쿼리를 생성해야 합니다.

    ### 입력 데이터:
    나의 프로필: {persona}
    선택한 에피소드: {selected_episode}
    질문과 응답: {qa_pairs}

    ### 출력: 다음 형식의 JSON으로 응답하세요:

    {{
        "user_emotion": "나의 현재 감정 상태 (기쁨, 슬픔, 스트레스, 지침, 설렘 등)를 쉼표로 구분하세요.",
        "user_episode": "오늘 하루의 특별한 상황이나 이벤트",
        "food_query": "나에게 추천할 만한 개인화된 검색 문장을 한 문장으로 작성하세요. 특정 음식을 언급하지 마세요.",
        "recommend_reason": "재미있고 공감가는 표현을 사용하여 추천하는 이유를 서술하세요"
    }}

    food_query는 다음 요소를 고려하여 작성하세요:
    - 나의 현재 감정 상태에 도움이 될 수 있는 음식의 특성
    - 나의 하루를 더 나아지게 할 수 있는 음식 요소
    - 나의 상황과 연결된 음식의 정서적 가치
    - 음식의 분위기나 경험적 측면 (위로, 응원, 활력, 안정감 등)
    """

    claude = BedrockClaude(region='us-east-1', modelId=BedrockModel.SONNET_3_7_CR)
    # for chunk in claude.converse_stream(text=PROMPT):
    #     yield chunk
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
    
    
def lambda_handler(event, context):
    user_id = event['user_id']
    persona = event['persona']
    selected_episode = event['selected_episode']
    qa_pairs = event['qa_pairs']

    # persona = "이 인물은 30대 후반의 남성으로 보입니다. 안경을 쓰고 있어 지적인 이미지를 가지고 있으며, 웃는 표정으로 보아 친근하고 쾌활한 성격을 가지고 있는 것으로 보입니다. 아마도 학문적인 분야에서 일하는 직업을 가지고 있을 것 같습니다."
    # selected_episode = "어느 날 동료들과 함께 커피를 마시던 중, 새로운 아이디어에 대해 열띤 토론을 벌였습니다. 그는 자신의 아이디어를 설명하며 열정적으로 손짓을 하였고, 결국 그의 아이디어가 채택되었습니다. :짠:",
    # qa_pairs = [
    # {
    #     "question":"이번에 동료들과 함께 열띬로 토론한 아이디어에 대해 생각해 보았을 때, 당신이 가장 좋아하는 토론 주제는 무엇인가요?",
    #     "answer": "과학 기술 관련 주제"
    # },
    # {
    #     "question":"동료들과 아이디어를 토론하며 열정적으로 손짓을 하던 모습을 보고, 당신은 어떤 활동을 통해 자신의 생각을 표현하는 것을 좋아하나요?",
    #     "answer": "예술적인 표현을 통해 자신의 생각을 전달하는 것, 예를 들어 그림이나 음악"
    # },
    # {
    #     "question":"이 인물이 취미 활동으로 가장 즐기는 것은 무엇인가요? 아래 중 하나를 선택해 주세요.",
    #     "answer": "커피숍에서 다양한 음료를 시음하기"
    # }
    # ]

    recommend = generate_recommendation(persona, selected_episode, qa_pairs)
    print(recommend)    

    result = {
        "user_id": user_id,
        "recommend": recommend
    }

    return {
        'statusCode': 200,
        'body': result
    }