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

def extract_json(str):
    try:
        str = str.replace('```json', '').replace('```', '')
        return json.loads(str)
    except Exception as e:
        print(f"Error: {str}")
        return {}
    
def generate_next_question(persona, selected_episode, previous_qa=None, question_number=1):
    # Format previous Q&A information
    previous_qa_text = ""
    if previous_qa and len(previous_qa) > 0:
        previous_qa_text = "이전 질문과 답변:\n"
        for q, a in previous_qa.items():
            previous_qa_text += f"Q: {q}\nA: {a}\n"
    
    PROMPT = f"""너는 주어진 내 정보를 보고 분위기와 성격을 추론하는 감성적인 AI 스토리텔러야. 일상을 기반으로 스토리를 만들 거야.
    주어진 페르소나와 에피소드를 보고, 나의 취향을 파악하기 위한 질문 하나를 간결한 한 문장으로 만들어주세요. 질문은 15글자를 넘지 마세요. 이 질문은 전체 3개 질문 중 {question_number}번째 질문입니다.
    질문에는 3개의 옵션을 포함해야 합니다.

    주어진 나의 정보:
    - 페르소나: {persona}
    - 에피소드: {selected_episode}
    {previous_qa_text}
    
    {question_number}번째 질문을 생성할 때 이전 질문과 답변을 고려하여 새로운 측면의 취향을 물어보세요.

    아래와 같은 json 포맷으로 답변하세요. 항상 한글로 서술하세요:
    - question: str
    - options: list[str]
    """

    claude = BedrockClaude(region='us-east-1', modelId=BedrockModel.NOVA_MICRO_CR)
    res = claude.converse(text=PROMPT)
    question_data = extract_json(res)
    
    # Format conversion (return single question object)
    if 'question' in question_data and 'options' in question_data:
        return question_data
    
    # Handle case where previous format (questions list) is returned
    if 'questions' in question_data and len(question_data['questions']) > 0:
        return question_data['questions'][0]
    
    # Return default question (in case of error)
    return {
        'question': f"오늘 기분이 어떠세요?",
        'options': ["신남", "화남", "지루함", "귀찮음"]
    }

def lambda_handler(event, context):

    # persona = "이 인물은 30대 후반의 남성으로 보입니다. 안경을 쓰고 있어 지적인 이미지를 가지고 있으며, 웃는 표정으로 보아 친근하고 쾌활한 성격을 가지고 있는 것으로 보입니다. 아마도 학문적인 분야에서 일하는 직업을 가지고 있을 것 같습니다."
    # episode = [
    #     "어느 날 동료들과 함께 커피를 마시던 중, 새로운 아이디어에 대해 열띤 토론을 벌였습니다. 그는 자신의 아이디어를 설명하며 열정적으로 손짓을 하였고, 결국 그의 아이디어가 채택되었습니다. :짠:",
    #     "회사에서 새로운 프로젝트가 시작되었을 때, 그는 팀원들에게 새로운 기술을 소개하는 워크숍을 주도하였습니다. 그의 설명은 매우 명확하고 재미있어서 팀원들은 모두 즐겁게 참여하였습니다. :컴퓨터:",
    #     "퇴근 후 친구들과 함께 게임을 하던 중, 그는 게임에서 승리하여 친구들에게 농담을 하며 웃음을 자아냈습니다. 그의 재치 있는 농담에 친구들은 모두 웃음을 터뜨렸습니다. :비디오_게임:"
    # ]

    print(f"event: {event}")
    
    user_id = event['user_id']
    persona = event['persona']  
    episode = event['episode']
    select = event['select']

    print(f"persona: {persona}")
    print(f"episode: {episode}")
    
    generated_questions = []
    selected_episode = episode[select]

    index = 0
    max_attempts = 10
    target_questions = 3

    while len(generated_questions) < target_questions and index < max_attempts:
        question = generate_next_question(
            persona=persona,
            selected_episode=selected_episode,    
            question_number=len(generated_questions) + 1  # 현재 생성된 질문 수 + 1을 question_number로 전달
        )
        
        # Check for duplicates by comparing question content
        is_duplicate = False
        for existing_question in generated_questions:
            if existing_question['question'] == question['question']:
                is_duplicate = True
                break
        
        if not is_duplicate:
            generated_questions.append(question)
        
        index += 1

    # Verify if we got exactly 3 questions
    if len(generated_questions) != target_questions:
        print(f"Warning: Could not generate {target_questions} unique questions after {max_attempts} attempts")

    print(f"generated_questions: {generated_questions}")
    
    result = {
        "user_id": user_id,
        "generated_questions": generated_questions
    }

    return {
        'statusCode': 200,
        'body': json.dumps(result, ensure_ascii=False)
    }
