import boto3
import json
import re
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
#### 오늘의 당신은?
- **현재 감정**: 성취감, 열정, 기쁨
- **상황**: 동료들과의 토론에서 아이디어가 채택되어 성공적인 순간을 경험함
#### 추천 음식
```txt
과학적 호기심과 예술적 감성이 공존하는 당신에게, 성취의 기쁨을 더욱 풍성하게 해줄 색감이 화려하고 다양한 맛의 조화가 돋보이는 한식 요리
```
#### 추천 이유
오늘 당신은 마치 완벽한 커피 한 잔처럼 균형 잡힌 하루를 보내셨군요! 과학 기술에 대한 열정과 예술적 감성을 모두 갖춘 당신의 아이디어가 빛을 발한 특별한 날이니, 그 성취감을 더욱 풍성하게 해줄 음식이 필요합니다.
마치 다양한 커피를 음미하듯 여러 맛이 조화롭게 어우러진 한식이 어떨까요? 색감이 화려한 음식은 당신의 예술적 감성을 만족시키고, 다채로운 맛의 조합은 과학적 호기심을 자극할 거예요. 성공의 짜릿함을 입안 가득 느끼며, 오늘의 기쁨을 더욱 특별하게 기념해보세요. 당신의 빛나는 아이디어처럼, 오늘 저녁도 빛나길 바랍니다!
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

result = {
    "img_key": food_data.get('img_key', ''),
    "review": food_data.get('review', ''),
    "name": food_data.get('name', ''),
    "id": food_data.get('id', ''),
    "item": item,
    "url2": url2,
    "url3": url3
}    
print(f"result: {result}")