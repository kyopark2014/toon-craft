import boto3
import json
from botocore.config import Config
from langchain_aws.embeddings import BedrockEmbeddings


class BedrockEmbedding():
    def __init__(self, region='us-west-2'):
        self.region = region
        self.bedrock = boto3.client(
            service_name = 'bedrock-runtime',
            region_name = self.region,
            config = Config(
                connect_timeout=120,
                read_timeout=120,
                retries={'max_attempts': 5}
            ),
        )

        self.multimodalId = 'amazon.titan-embed-image-v1'
        self.multimodal = BedrockEmbeddings(
            client=self.bedrock,
            region_name = self.region,
            model_id = self.multimodalId
        )

        self.textEmbeddingId = 'amazon.titan-embed-text-v2:0'
        self.textmodal = BedrockEmbeddings(
            client=self.bedrock,
            region_name = self.region,
            model_id = self.textEmbeddingId
        )
    
    '''
    Multimodal Embedding
    '''
    def embedding_multimodal(self, text=None, image=None):
        body = dict()
        if text is not None: body['inputText'] = text
        if image is not None: body['inputImage'] = image

        try:
            res = self.bedrock.invoke_model(
                body=json.dumps(body),
                modelId=self.multimodalId,
                accept="application/json",
                contentType="application/json"
            )
            return json.loads(res.get("body").read()).get("embedding")
        except Exception as e:
            print(e)
            return []


    '''
    Text Embedding
    '''
    def embedding_text(self, text=None):
        body = dict()
        if text is not None: body['inputText'] = text
        
        try:
            res = self.bedrock.invoke_model(
                body=json.dumps(body),
                modelId=self.textEmbeddingId,
                accept="application/json",
                contentType="application/json"
            )
            return json.loads(res.get("body").read()).get("embedding")
        except Exception as e:
            print(e)
            return []
