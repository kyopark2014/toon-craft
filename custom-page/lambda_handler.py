import json
import os
import re
import urllib3
import boto3
from datetime import datetime
import logging
import qrcode
from io import BytesIO

# Configure logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS Profile Configuration
session = boto3.Session(profile_name='hur')
s3_client = session.client('s3')

# AWS Lambda Configuration
# s3_client = boto3.client('s3')

# S3 버킷 설정
BUCKET_NAME = 'tooncraft-custom'

def lambda_handler(event, context):
    """
    Lambda handler that processes input JSON and generates HTML content
    """
    # Print entire event for debugging
    print("Lambda Event:", json.dumps(event, indent=2, ensure_ascii=False))
    
    try:
        # 이벤트 데이터 파싱
        if isinstance(event, str):
            event = json.loads(event)
        
        # 필요한 데이터 추출
        id = event.get('id', '')
        episode = event.get('episode', '')
        persona = event.get('persona', '')
        recommend_id = event.get('recommend_id', '')
        device_id = event.get('device_id', '')
        user_id = event.get('user_id', '')
        
        # item 정보 추출
        item = event.get('item', {})
        menu = item.get('menu', [])
        contact = item.get('contact', {})
        media = item.get('media', {})
        operating_hours = item.get('operating_hours', {})
        review = item.get('review', '')
        restaurant_name = item.get('name', '')
        
        # 미디어 목록 추출 - 단순화된 로직
        media_list = event.get('media_list', [])
        
        # 질문 및 답변 추출
        questions_answers = event.get('questions', [])
        
        # recommend 정보 추출
        recommend_data = event.get('recommend', {})
        
        # 추천 결과 정보 추출
        recommendation_result = {}
        if 'result' in event and 'recommendation_result' in event['result']:
            recommendation_result = event['result']['recommendation_result']
        
        # HTML 템플릿 가져오기
        # template_url = "https://d1399sbeavfl0z.cloudfront.net/index.html"
        template_url = ""
        http = urllib3.PoolManager()
        try:
            response = http.request('GET', template_url)
            if response.status == 200:
                html_template = response.data.decode('utf-8')
                logger.info("Successfully fetched HTML template from CloudFront")
            else:
                raise Exception(f"Failed to fetch template: {response.status}")
        except Exception as e:
            # 원격 템플릿을 가져오지 못한 경우 로컬 파일 사용
            html_template_path = os.path.join(os.path.dirname(__file__), 'index.html')
            with open(html_template_path, 'r', encoding='utf-8') as file:
                html_template = file.read()
            logger.info("Using local HTML template file")
        
        # 현재 날짜 포맷팅
        current_date = datetime.now().strftime('%Y.%m.%d')
        
        # 프로필 섹션 업데이트
        profile_pattern = r'<div class="profile-content">.*?</div>'
        profile_replacement = f'''
            <div style="text-align: center; margin-bottom: 30px;">
                <img src="{event.get('gen_image', '')}" alt="Generated Profile Image" style="width: 100%; max-width: 600px; border-radius: 20px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);">
            </div>
            <div style="background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); padding: 30px; border-radius: 20px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05); margin: 20px 0;">
                <div style="font-family: 'Gaegu', cursive; font-size: 32px; font-weight: 700; color: #495057; text-align: center; margin-bottom: 20px; position: relative;">
                    <span style="background: linear-gradient(transparent 60%, #ffd700 40%);">당신은 이런 사람이군요!</span>
                    <div style="position: absolute; bottom: -10px; left: 50%; transform: translateX(-50%); width: 100px; height: 3px; background: linear-gradient(90deg, transparent, #ffd700, transparent);"></div>
                </div>
                <div class="profile-content" style="font-size: 20px; line-height: 1.6; color: #495057; text-align: center; padding: 0 20px;">{persona}</div>
            </div>
        '''
        html_template = re.sub(profile_pattern, profile_replacement, html_template, flags=re.DOTALL)
        logger.info("Updated profile section with enhanced design")
        
        # 중복된 말풍선 제거
        speech_bubble_pattern = r'나는 500곳이 넘는 맛집을 다녀왔지\. 내 추천은 믿어도 좋아'
        # 첫 번째 말풍선만 유지하고 나머지 제거
        count = 0
        def replace_speech_bubble(match):
            nonlocal count
            count += 1
            return match.group(0) if count == 1 else ''
        
        html_template = re.sub(speech_bubble_pattern, replace_speech_bubble, html_template)
        logger.info("Removed duplicate speech bubbles")
        
        # CSS 애니메이션 스타일 정의
        animation_styles = '''
            <style>
                @keyframes float {
                    0%, 100% { transform: translateY(0); }
                    50% { transform: translateY(-5px); }
                }
                @keyframes bounce {
                    0%, 100% { transform: scale(1); }
                    50% { transform: scale(1.1); }
                }
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
                
                /* 모바일 최적화 스타일 */
                @media screen and (max-width: 768px) {
                    .container {
                        padding: 15px;
                        width: 100%;
                        box-sizing: border-box;
                    }
                    
                    .title {
                        font-size: 24px !important;
                        margin-bottom: 15px !important;
                    }
                    
                    .subtitle {
                        font-size: 20px !important;
                        margin-bottom: 10px !important;
                    }
                    
                    .content {
                        font-size: 16px !important;
                        line-height: 1.5 !important;
                    }
                    
                    .image-container {
                        flex-direction: column !important;
                        gap: 15px !important;
                    }
                    
                    .image-wrapper {
                        width: 100% !important;
                        height: auto !important;
                        aspect-ratio: 4/3 !important;
                    }
                    
                    .qa-item {
                        padding: 15px !important;
                        margin-bottom: 15px !important;
                    }
                    
                    .media-grid {
                        grid-template-columns: 1fr !important;
                        gap: 20px !important;
                        padding: 20px !important;
                    }
                }
            </style>
        '''

        # 시선 유도 디자인 추가
        eye_guide_pattern = r'<div style="word-break: keep-all; font-size: 28px; mso-line-height: exactly; line-height: 40px;">당신은 이런 사람이군요! <span class="emoji">😊</span></div>'
        eye_guide_replacement = f'''
            <div style="text-align: center; margin: 20px 0 40px; position: relative;">
                {animation_styles}
                <div style="position: relative; height: 100px; display: flex; flex-direction: column; align-items: center;">
                    <div style="width: 2px; height: 40px; background: linear-gradient(to bottom, #ffd700, transparent); margin: 0 auto;"></div>
                    <div style="font-family: 'Gaegu', cursive; font-size: 28px; font-weight: 700; color: #495057; margin: 10px 0; display: flex; align-items: center; justify-content: center; gap: 8px; animation: float 2s ease-in-out infinite;">
                        <span style="font-size: 24px; animation: spin 3s linear infinite;">✨</span>
                        <span style="background: linear-gradient(transparent 60%, #ffd700 40%); padding: 0 10px; animation: bounce 1s ease-in-out infinite;">취향 스캔 중</span>
                        <span style="font-size: 24px; animation: spin 3s linear infinite reverse;">✨</span>
                    </div>
                    <div style="width: 2px; height: 40px; background: linear-gradient(to bottom, #ffd700, transparent); margin: 0 auto;"></div>
                    <div style="width: 12px; height: 12px; border-right: 2px solid #ffd700; border-bottom: 2px solid #ffd700; transform: rotate(45deg); margin: -6px auto 0;"></div>
                </div>
            </div>
        '''
        html_template = re.sub(eye_guide_pattern, eye_guide_replacement, html_template)
        logger.info("Updated eye-guiding design with animated text")
        
        # QA 섹션 업데이트 - 완전히 새로운 내용으로 교체
        qa_items = []
        background_colors = [
            '#FFE4E1',  # 미스티 로즈
            '#E0FFFF',  # 라이트 시안
            '#F0FFF0'   # 허니듀
        ]
        for i, qa in enumerate(questions_answers):
            question = qa.get('question', '')
            answer = qa.get('answer', '')
            bg_color = background_colors[i % len(background_colors)]
            logger.info(f"Creating QA item {i+1} with question: {question} and answer: {answer}")
            qa_items.append(f'''
                <div class="qa-item" style="margin-bottom: 30px; padding: 20px; background: {bg_color}; border-radius: 15px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);">
                    <div class="question" style="font-size: 18px; color: #6c757d; margin-bottom: 15px; font-style: italic;">Q. {question}</div>
                    <div class="answer" style="font-size: 22px; line-height: 1.6; color: #495057; font-weight: 700;">A. {answer}</div>
                </div>
            ''')
        
        # QA 섹션 전체를 새로운 내용으로 완전히 교체
        qa_section_pattern = r'<div class="qa-section-sample">.*?</div>'
        qa_section_replacement = f'''
            <div class="qa-section" style="max-width: 800px; margin: 0 auto; padding: 20px;">
                {qa_items[0] if len(qa_items) > 0 else ''}
                {qa_items[1] if len(qa_items) > 1 else ''}
                {qa_items[2] if len(qa_items) > 2 else ''}
            </div>
        '''
        # -sample이 붙은 QA 섹션을 찾아서 새로운 내용으로 대체
        html_template = re.sub(qa_section_pattern, qa_section_replacement, html_template, flags=re.DOTALL)
        logger.info(f"Updated QA section with {len(qa_items)} answers")
        
        # 디버깅을 위해 최종 HTML에서 QA 섹션 확인
        qa_section_match = re.search(r'<div class="qa-section">.*?</div>', html_template, re.DOTALL)
        if qa_section_match:
            logger.info(f"Final QA section in HTML: {qa_section_match.group(0)}")
        else:
            logger.warning("QA section not found in final HTML")
        
        # 추천 섹션 업데이트
        recommendation_pattern = r'<div class="recommendation-section-sample">.*?</div>'
        recommendation_replacement = f'''
            <div class="recommendation-section">
                <div class="user-emotion" style="font-size: 20px;">{menu[0] if len(menu) > 0 else ''}</div>
                <div class="recommendation-description" style="font-size: 22px; line-height: 1.6;">
                    {recommendation_result.get('description', '')}
                </div>
                <div class="recommendation-reasons">
                    <div class="reason-item" style="font-size: 20px; line-height: 1.6;">
                        {recommendation_result.get('reason_1', '')}
                    </div>
                    <div class="reason-item" style="font-size: 20px; line-height: 1.6;">
                        {recommendation_result.get('reason_2', '')}
                    </div>
                    <div class="reason-item" style="font-size: 20px; line-height: 1.6;">
                        {recommendation_result.get('reason_3', '')}
                    </div>
                </div>
            </div>
        '''
        # -sample이 붙은 추천 섹션을 찾아서 새로운 내용으로 대체
        html_template = re.sub(recommendation_pattern, recommendation_replacement, html_template, flags=re.DOTALL)
        logger.info("Updated recommendation section")
        
        # 일러스트 섹션 업데이트
        illustration_pattern = r'<div class="illustration-container">.*?</div>'
        illustration_replacement = f'''
            <div style="text-align: center; margin: 20px 0 40px; position: relative;">
                {animation_styles}
                <div style="position: relative; height: 100px; display: flex; flex-direction: column; align-items: center;">
                    <div style="width: 2px; height: 40px; background: linear-gradient(to bottom, #ffd700, transparent); margin: 0 auto;"></div>
                    <div style="font-family: 'Gaegu', cursive; font-size: 28px; font-weight: 700; color: #495057; margin: 10px 0; display: flex; align-items: center; justify-content: center; gap: 8px; animation: float 2s ease-in-out infinite;">
                        <span style="font-size: 24px; animation: spin 3s linear infinite;">✨</span>
                        <span style="background: linear-gradient(transparent 60%, #ffd700 40%); padding: 0 10px; animation: bounce 1s ease-in-out infinite;">입맛 저격 메뉴 고르는 중</span>
                        <span style="font-size: 24px; animation: spin 3s linear infinite reverse;">✨</span>
                    </div>
                    <div style="width: 2px; height: 40px; background: linear-gradient(to bottom, #ffd700, transparent); margin: 0 auto;"></div>
                    <div style="width: 12px; height: 12px; border-right: 2px solid #ffd700; border-bottom: 2px solid #ffd700; transform: rotate(45deg); margin: -6px auto 0;"></div>
                </div>
            </div>
            <div style="text-align: center; margin: 30px 0;">
                <div style="position: relative; display: inline-block;">
                    <div style="word-break: keep-all; font-size: 38px; mso-line-height: exactly; line-height: 44px; font-family: 'Gaegu', cursive; font-weight: 700; color: #333; padding: 30px 50px; background: #f8f9fa; border-radius: 10px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.1); border: 2px solid #e9ecef; transform: rotate(-1deg);">
                        <div style="position: absolute; top: 10px; left: 10px; width: 20px; height: 20px; background: #e9ecef; border-radius: 50%;"></div>
                        <div style="position: absolute; top: 10px; right: 10px; width: 20px; height: 20px; background: #e9ecef; border-radius: 50%;"></div>
                        <div style="position: absolute; bottom: 10px; left: 10px; width: 20px; height: 20px; background: #e9ecef; border-radius: 50%;"></div>
                        <div style="position: absolute; bottom: 10px; right: 10px; width: 20px; height: 20px; background: #e9ecef; border-radius: 50%;"></div>
                        {recommendation_result.get('title', '')}
                    </div>
                </div>
            </div>
            <div class="illustration-container">
                <img src="https://d710ry44thcvf.cloudfront.net/contents/{recommend_id}/review_illust_food.png" alt="음식 일러스트">
            </div>
        '''
        html_template = re.sub(illustration_pattern, illustration_replacement, html_template, flags=re.DOTALL)
        
        # 디버깅을 위해 recommendation_result 내용 로깅
        logger.info(f"Recommendation result data: {json.dumps(recommendation_result, ensure_ascii=False)}")
        
        # 2x2 그리드 섹션 추가
        media_grid_section = f'''
            <div style="text-align: center; margin: 20px 0 40px; position: relative;">
                {animation_styles}
                <div style="position: relative; height: 100px; display: flex; flex-direction: column; align-items: center;">
                    <div style="width: 2px; height: 40px; background: linear-gradient(to bottom, #ffd700, transparent); margin: 0 auto;"></div>
                    <div style="font-family: 'Gaegu', cursive; font-size: 28px; font-weight: 700; color: #495057; margin: 10px 0; display: flex; align-items: center; justify-content: center; gap: 8px; animation: float 2s ease-in-out infinite;">
                        <span style="font-size: 24px; animation: spin 3s linear infinite;">✨</span>
                        <span style="background: linear-gradient(transparent 60%, #ffd700 40%); padding: 0 10px; animation: bounce 1s ease-in-out infinite;">당신을 위한 맛 레시피 완성</span>
                        <span style="font-size: 24px; animation: spin 3s linear infinite reverse;">✨</span>
                    </div>
                    <div style="width: 2px; height: 40px; background: linear-gradient(to bottom, #ffd700, transparent); margin: 0 auto;"></div>
                    <div style="width: 12px; height: 12px; border-right: 2px solid #ffd700; border-bottom: 2px solid #ffd700; transform: rotate(45deg); margin: -6px auto 0;"></div>
                </div>
            </div>
            <div class="media-grid" style="display: grid; grid-template-columns: repeat(2, 1fr); gap: 40px; width: 100%; max-width: 800px; margin: 0 auto; background: #fff; padding: 40px; border-radius: 30px; box-shadow: 0 15px 30px rgba(0, 0, 0, 0.12); box-sizing: border-box;">
                <div class="media-item" style="width: 100%;">
                    <div class="step-label" style="font-size: 24px; margin-bottom: 20px; color: #333; font-weight: 600;">Step 1. 재료 준비</div>
                    {f'<video controls autoplay muted loop playsinline style="width: 100%; border-radius: 20px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);"><source src="{media_list[0]}" type="video/mp4"></video>' if len(media_list) > 0 and media_list[0].lower().endswith(('.mp4', '.mov', '.avi', '.webm')) else f'<img src="{media_list[0] if len(media_list) > 0 else ""}" border="0" alt="재료 준비" style="width: 100%; border-radius: 20px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);">'}
                </div>
                <div class="media-item" style="width: 100%;">
                    <div class="step-label" style="font-size: 24px; margin-bottom: 20px; color: #333; font-weight: 600;">Step 2. 조리 과정</div>
                    {f'<video controls autoplay muted loop playsinline style="width: 100%; border-radius: 20px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);"><source src="{media_list[1]}" type="video/mp4"></video>' if len(media_list) > 1 and media_list[1].lower().endswith(('.mp4', '.mov', '.avi', '.webm')) else f'<img src="{media_list[1] if len(media_list) > 1 else ""}" border="0" alt="조리 과정" style="width: 100%; border-radius: 20px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);">'}
                </div>
                <div class="media-item" style="width: 100%;">
                    <div class="step-label" style="font-size: 24px; margin-bottom: 20px; color: #333; font-weight: 600;">Step 3. 마무리</div>
                    {f'<video controls autoplay muted loop playsinline style="width: 100%; border-radius: 20px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);"><source src="{media_list[2]}" type="video/mp4"></video>' if len(media_list) > 2 and media_list[2].lower().endswith(('.mp4', '.mov', '.avi', '.webm')) else f'<img src="{media_list[2] if len(media_list) > 2 else ""}" border="0" alt="마무리" style="width: 100%; border-radius: 20px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);">'}
                </div>
                <div class="media-item" style="width: 100%;">
                    <div class="step-label" style="font-size: 24px; margin-bottom: 20px; color: #333; font-weight: 600;">Step 4. 완성</div>
                    {f'<video controls autoplay muted loop playsinline style="width: 100%; border-radius: 20px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);"><source src="{media_list[3]}" type="video/mp4"></video>' if len(media_list) > 3 and media_list[3].lower().endswith(('.mp4', '.mov', '.avi', '.webm')) else f'<img src="{media_list[3] if len(media_list) > 3 else ""}" border="0" alt="완성" style="width: 100%; border-radius: 20px; box-shadow: 0 8px 16px rgba(0, 0, 0, 0.1);">'}
                </div>
                <div class="photo-strip-date" style="grid-column: 1 / -1; color: #666; font-size: 18px; margin-top: 30px; text-align: center; font-family: 'Gaegu', cursive; font-style: italic;">{current_date}</div>
            </div>
            <div style="text-align: center; margin: 20px 0 40px; position: relative;">
                {animation_styles}
                <div style="position: relative; height: 100px; display: flex; flex-direction: column; align-items: center;">
                    <div style="width: 2px; height: 40px; background: linear-gradient(to bottom, #ffd700, transparent); margin: 0 auto;"></div>
                    <div style="font-family: 'Gaegu', cursive; font-size: 28px; font-weight: 700; color: #495057; margin: 10px 0; display: flex; align-items: center; justify-content: center; gap: 8px; animation: float 2s ease-in-out infinite;">
                        <span style="font-size: 24px; animation: spin 3s linear infinite;">✨</span>
                        <span style="background: linear-gradient(transparent 60%, #ffd700 40%); padding: 0 10px; animation: bounce 1s ease-in-out infinite;">먹으러 가볼까?</span>
                        <span style="font-size: 24px; animation: spin 3s linear infinite reverse;">✨</span>
                    </div>
                    <div style="width: 2px; height: 40px; background: linear-gradient(to bottom, #ffd700, transparent); margin: 0 auto;"></div>
                    <div style="width: 20px; height: 20px; background: #ffd700; border-radius: 50%; margin: -6px auto 0;"></div>
                </div>
            </div>
            <div style="max-width: 800px; margin: 0 auto; padding: 30px; background: #fff; border-radius: 20px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);">
                <div style="text-align: center; margin-bottom: 25px; padding: 15px;">
                    <div style="font-family: 'Gaegu', cursive; font-size: clamp(24px, 5vw, 32px); font-weight: 700; color: #333; margin-bottom: 10px;">{restaurant_name}</div>
                    <div style="margin-bottom: 20px;">
                        <div style="font-size: clamp(16px, 4vw, 20px); color: #666; margin-bottom: 15px;">
                            <span style="display: inline-block; margin-right: 15px;">🕒 {operating_hours.get('hours', '')}</span>
                        </div>
                        <div style="font-size: clamp(14px, 3.5vw, 18px); color: #666; line-height: 1.6;">
                            <span style="display: inline-block;">📍 {contact.get('address', '')}</span>
                        </div>
                    </div>
                    <div style="display: flex; justify-content: center; gap: 20px; margin: 30px auto; width: 100%; max-width: 800px; flex-wrap: wrap;">
                        <div style="position: relative; width: clamp(150px, 45vw, 200px); height: clamp(112px, 33.75vw, 150px);">
                            <img src="https://d710ry44thcvf.cloudfront.net/{media.get('photos', [''])[1]}" alt="식당 사진 1" style="width: 100%; height: 100%; object-fit: cover; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);" onerror="this.onerror=null; this.src='https://via.placeholder.com/200x150?text=Image+Not+Found';">
                        </div>
                        <div style="position: relative; width: clamp(150px, 45vw, 200px); height: clamp(112px, 33.75vw, 150px);">
                            <img src="https://d710ry44thcvf.cloudfront.net/{media.get('photos', [''])[2]}" alt="식당 사진 2" style="width: 100%; height: 100%; object-fit: cover; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);" onerror="this.onerror=null; this.src='https://via.placeholder.com/200x150?text=Image+Not+Found';">
                        </div>
                    </div>
                    <div style="margin-top: 30px; padding: clamp(15px, 4vw, 25px); background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%); border-radius: 15px; box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);">
                        <div style="font-family: 'Gaegu', cursive; font-size: clamp(20px, 4.5vw, 24px); color: #495057; font-weight: 700; margin-bottom: 15px;">리뷰</div>
                        <div style="font-size: clamp(16px, 4vw, 20px); line-height: 1.6; color: #495057; text-align: left; padding: 0 clamp(10px, 3vw, 20px);">{review}</div>
                    </div>
                </div>
            </div>
        '''
        
        # 하드코딩된 미디어 그리드 섹션을 찾아서 새로운 내용으로 대체
        media_grid_pattern = r'<div class="section-title-sample">.*?</div>.*?<div class="media-grid-sample">.*?</div>'
        html_template = re.sub(media_grid_pattern, media_grid_section, html_template, flags=re.DOTALL)
        logger.info(f"Updated media grid section with {len(media_list)} media items")
        
        # step-label-sample과 관련된 모든 요소 제거
        step_label_pattern = r'<div class="step-label-sample">.*?</div>.*?<(?:img|video)[^>]*>'
        html_template = re.sub(step_label_pattern, '', html_template, flags=re.DOTALL)
        logger.info("Removed step-label-sample divs and their associated media elements")
        
        # -sample이 붙은 모든 div 요소 제거 (미디어 그리드 섹션 제외)
        sample_div_pattern = r'<div[^>]*class="[^"]*-sample[^"]*"[^>]*>(?!.*?media-grid-sample).*?</div>'
        html_template = re.sub(sample_div_pattern, '', html_template, flags=re.DOTALL)
        logger.info("Removed all divs with -sample postfix except media grid section")
        
        # S3에 HTML 파일 저장
        file_name = f'page/{id}.html'
        
        try:
            # Get device_id from event
            device_id = event.get('device_id', '')
            print(f"Processing request for device_id: {device_id}")
            
            # Upload to original page path
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=file_name,
                Body=html_template.encode('utf-8'),
                ContentType='text/html',
                CacheControl='max-age=3600'
            )
            print(f"Successfully uploaded to original path: s3://{BUCKET_NAME}/{file_name}")
            logger.info(f"Successfully uploaded HTML file to S3: {BUCKET_NAME}/{file_name}")
            
            # Upload to device-specific path if device_id matches
            if device_id == 'ap-northeast-1:3c3f82b4-f743-c947-446f-76887dd881c6':
                device_path = 'device1/index.html'
                # Check if file exists before overwriting
                try:
                    s3_client.head_object(Bucket=BUCKET_NAME, Key=device_path)
                    print(f"Found existing index.html in device1, will overwrite: s3://{BUCKET_NAME}/{device_path}")
                except:
                    print(f"No existing index.html found in device1, creating new file: s3://{BUCKET_NAME}/{device_path}")
                
                s3_client.put_object(
                    Bucket=BUCKET_NAME,
                    Key=device_path,
                    Body=html_template.encode('utf-8'),
                    ContentType='text/html',
                    CacheControl='max-age=3600'
                )
                print(f"Successfully uploaded to device1 path: s3://{BUCKET_NAME}/{device_path}")
                logger.info(f"Successfully uploaded HTML file to device1 path: {BUCKET_NAME}/{device_path}")
                
                # Verify device1 index.html
                try:
                    s3_client.head_object(Bucket=BUCKET_NAME, Key=device_path)
                    print(f"Verified device1 index.html exists at: s3://{BUCKET_NAME}/{device_path}")
                except Exception as verify_error:
                    print(f"Failed to verify device1 index.html: {str(verify_error)}")
                    logger.error(f"Failed to verify device1 index.html: {str(verify_error)}")
                    
            elif device_id == 'ap-northeast-1:3c3f82b4-f7a3-c0ea-1d28-1aab6e7218c5':
                device_path = 'device2/index.html'
                # Check if file exists before overwriting
                try:
                    s3_client.head_object(Bucket=BUCKET_NAME, Key=device_path)
                    print(f"Found existing index.html in device2, will overwrite: s3://{BUCKET_NAME}/{device_path}")
                except:
                    print(f"No existing index.html found in device2, creating new file: s3://{BUCKET_NAME}/{device_path}")
                
                s3_client.put_object(
                    Bucket=BUCKET_NAME,
                    Key=device_path,
                    Body=html_template.encode('utf-8'),
                    ContentType='text/html',
                    CacheControl='max-age=3600'
                )
                print(f"Successfully uploaded to device2 path: s3://{BUCKET_NAME}/{device_path}")
                logger.info(f"Successfully uploaded HTML file to device2 path: {BUCKET_NAME}/{device_path}")
                
                # Verify device2 index.html
                try:
                    s3_client.head_object(Bucket=BUCKET_NAME, Key=device_path)
                    print(f"Verified device2 index.html exists at: s3://{BUCKET_NAME}/{device_path}")
                except Exception as verify_error:
                    print(f"Failed to verify device2 index.html: {str(verify_error)}")
                    logger.error(f"Failed to verify device2 index.html: {str(verify_error)}")
            
            # Verify the original file exists in S3
            try:
                s3_client.head_object(Bucket=BUCKET_NAME, Key=file_name)
                logger.info(f"Verified file exists in S3: {BUCKET_NAME}/{file_name}")
            except Exception as verify_error:
                logger.error(f"Failed to verify file in S3: {str(verify_error)}")
                
        except Exception as e:
            logger.error(f"Failed to upload to S3: {str(e)}")
            raise Exception(f"Failed to upload to S3: {str(e)}")
        
        url = f'https://d1399sbeavfl0z.cloudfront.net/{file_name}'

        # Generate QR code
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)

        # Create QR code image
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Convert image to bytes
        img_byte_arr = BytesIO()
        qr_image.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        # Upload QR code to S3
        qr_file_name = f'qr/{id}.png'
        try:
            s3_client.put_object(
                Bucket=BUCKET_NAME,
                Key=qr_file_name,
                Body=img_byte_arr,
                ContentType='image/png',
                CacheControl='max-age=3600'
            )
            logger.info(f"Successfully uploaded QR code to S3: {BUCKET_NAME}/{qr_file_name}")
        except Exception as e:
            logger.error(f"Failed to upload QR code to S3: {str(e)}")
            raise Exception(f"Failed to upload QR code to S3: {str(e)}")

        # 응답 생성
        response = {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'message': 'HTML file generated and uploaded successfully',
                'file_name': file_name,
                'url': url
            })
        }
        
        return response
        
    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
            },
            'body': json.dumps({
                'error': str(e)
            })
        }

# 로컬 테스트용 코드
if __name__ == "__main__":
    # 테스트 데이터 로드
    with open('event.json', 'r', encoding='utf-8') as f:
        test_data = json.load(f)
    
    # 핸들러 실행
    result = lambda_handler(test_data, None)
    
    # 결과 저장
    with open('output.html', 'w', encoding='utf-8') as f:
        f.write(result['body'])
    
    print("HTML 생성 완료: output.html")