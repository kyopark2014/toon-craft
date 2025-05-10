import boto3
import json
from genai_kit.aws.amazon_image import BedrockAmazonImage, ImageParams, NovaImageSize
from genai_kit.aws.bedrock import BedrockModel
from genai_kit.aws.claude import BedrockClaude

def extract_json(str):
    try:
        str = str.replace('```json', '').replace('```', '')
        return json.loads(str)
    except Exception as e:
        print(f"Error: {str}")
        return {}
    
def generate_questions(persona, selected_episode):
    PROMPT = f"""너는 주어진 내 정보를 보고 분위기와 성격을 추론하는 감성적인 AI 스토리텔러야. 일상을 기반으로 스토리를 만들 거야.
    주어진 페르소나와 에피소드를 보고, 나의 취향을 파악하기 위한 질문 3개를 각각 간결하고 재치있는 한 문장으로 만들어주세요.
    각 질문에는 3개의 옵션을 포함해야 합니다.

    주어진 나의 정보:
    - 페르소나: {persona}
    - 에피소드: {selected_episode}
    
    각 질문은 서로 다른 측면의 취향을 물어보세요.

    아래와 같은 json 포맷으로 답변하세요. 항상 한글로 서술하세요:
    - questions: list[object]
      - question: str
      - options: list[str]
    """

    claude = BedrockClaude(region='us-east-1', modelId=BedrockModel.NOVA_LITE_CR)
    res = claude.converse(text=PROMPT)
    question_data = extract_json(res)
    
    # Handle case where questions list is returned
    if 'questions' in question_data and len(question_data['questions']) > 0:
        return question_data['questions'][:3]  # Ensure we only return 3 questions
    
    # Return default questions (in case of error)
    return [{
        'question': "오늘 기분이 어떠세요?",
        'options': ["신남", "화남", "지루함", "귀찮음"]
    }, {
        'question': "어떤 활동을 선호하시나요?",
        'options': ["실내활동", "야외활동", "문화활동"]
    }, {
        'question': "주말에 무엇을 하고 싶으신가요?",
        'options': ["휴식", "취미활동", "친구만남"]
    }]

def lambda_handler(event, context):

    # persona = "이 인물은 30대 후반의 남성으로 보입니다. 안경을 쓰고 있어 지적인 이미지를 가지고 있으며, 웃는 표정으로 보아 친근하고 쾌활한 성격을 가지고 있는 것으로 보입니다. 아마도 학문적인 분야에서 일하는 직업을 가지고 있을 것 같습니다."
    # episode = [
    #     "어느 날 동료들과 함께 커피를 마시던 중, 새로운 아이디어에 대해 열띤 토론을 벌였습니다. 그는 자신의 아이디어를 설명하며 열정적으로 손짓을 하였고, 결국 그의 아이디어가 채택되었습니다. :짠:",
    #     "회사에서 새로운 프로젝트가 시작되었을 때, 그는 팀원들에게 새로운 기술을 소개하는 워크숍을 주도하였습니다. 그의 설명은 매우 명확하고 재미있어서 팀원들은 모두 즐겁게 참여하였습니다. :컴퓨터:",
    #     "퇴근 후 친구들과 함께 게임을 하던 중, 그는 게임에서 승리하여 친구들에게 농담을 하며 웃음을 자아냈습니다. 그의 재치 있는 농담에 친구들은 모두 웃음을 터뜨렸습니다. :비디오_게임:"
    # ]

    print(f"event: {event}")
    
    user_id = event['user_id']
    device_id = event.get('device_id', '1')
    persona = event['persona']  
    episode = event['episode']
    select = event['select']

    print(f"persona: {persona}")
    print(f"episode: {episode}")
    
    selected_episode = episode[select]
    generated_questions = generate_questions(persona, selected_episode)

    print(f"generated_questions: {generated_questions}")
    
    result = {
        "user_id": user_id,
        "device_id": device_id,
        "generated_questions": generated_questions
    }

    return {
        'statusCode': 200,
        'body': result,
    }
