import io
import os
import av
import base64
import requests
import tempfile
from io import BytesIO
from PIL import Image
from typing import Tuple
from IPython.display import display, HTML, Video, Image as IPythonImage


# Function to encode image from bytes or PIL.Image
def encode_image_base64(image, format="PNG", max_size=(2000, 2000)):
    # If the input is not an instance of PIL.Image, open it
    if not isinstance(image, Image.Image):
        image = Image.open(image)
    
    # Resize the image
    image.thumbnail(max_size, Image.Resampling.LANCZOS)

    # Save the image to buffer and encode as base64
    buffer = BytesIO()
    image.convert('RGB').save(buffer, format=format)
    encoded_image = base64.b64encode(buffer.getvalue())
    return encoded_image.decode('utf-8')

# Function to encode image from a URL
def encode_image_base64_from_url(img_url, format="PNG", max_size=(2000, 2000)):
    try:
        response = requests.get(img_url, timeout=10)
        response.raise_for_status()  # Raise an error for bad responses
        return encode_image_base64(BytesIO(response.content), format, max_size)
    except Exception as e:
        print(f"Error fetching image from URL: {e}")
        return None

# Function to encode image from a file path
def encode_image_base64_from_file(file_path, format="PNG", max_size=(2000, 2000)):
    try:
        with open(file_path, 'rb') as img_file:
            image_data = img_file.read()
        return encode_image_base64(BytesIO(image_data), format, max_size)
    except Exception as e:
        print(f"Error reading image from file: {e}")
        return None

# Display image given base64-encoded string
def display_image(utf8_encoded_image, height=200):
    if isinstance(utf8_encoded_image, str):
        html = f'<img src="data:image/png;base64,{utf8_encoded_image}" height="{height}"/>'
        display(HTML(html))
    elif isinstance(utf8_encoded_image, list):
        for img_str in utf8_encoded_image:
            html = f'<img src="data:image/png;base64,{img_str}" height="{height}"/>'
            display(HTML(html))


def display_video(video_bytes: bytes, width=800):
    temp_path = os.path.join(tempfile.gettempdir(), 'temp_video.mp4')
    with open(temp_path, 'wb') as f:
        f.write(video_bytes)
    video = Video(temp_path, embed=True, width=width, html_attributes="controls")
    display(video)

    try:
        os.remove(temp_path)
    except:
        pass

def base64_to_bytes(base64str: str):
    return BytesIO(base64.decodebytes(bytes(base64str, "utf-8")))

def base64_to_image(base64str: str):
    return Image.open(base64_to_bytes(base64str))

def save_base64_image(base64str: str, path: str):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    image = base64_to_image(base64str)
    image.save(path)


# 바이트 데이터를 사용하여 이미지를 표시하는 함수
def display_image_from_bytes(image_bytes, format='PNG', height=200):
    """
    바이트 데이터로부터 이미지를 표시합니다.
    """
    if isinstance(image_bytes, bytes):
        display(IPythonImage(data=image_bytes, format=format, height=height))
    elif isinstance(image_bytes, list):
        for img_bytes in image_bytes:
            display(IPythonImage(data=img_bytes, format=format, height=height))


# 이미지로부터 바이트 데이터를 얻는 함수
def get_image_bytes(image, format="PNG", max_size=(1000, 1000)):
    """
    이미지를 바이트 데이터로 변환합니다.
    Args:
        image: PIL.Image 객체 또는 이미지 파일 경로.
        format: 원하는 이미지 형식 (예: "JPEG", "PNG").
        max_size: 이미지의 최대 크기 (너비, 높이).
    Returns:
        bytes: 이미지의 바이트 데이터.
    """
    # 입력이 PIL.Image 객체가 아니면 이미지를 엽니다.
    if not isinstance(image, Image.Image):
        image = Image.open(image)
    
    # 이미지 크기 조정
    image.thumbnail(max_size, Image.Resampling.LANCZOS)

    # 이미지를 버퍼에 저장
    buffer = BytesIO()
    image.convert("RGB").save(buffer, format=format)
    image_bytes = buffer.getvalue()
    return image_bytes


# URL에서 이미지를 가져와 바이트 데이터를 얻는 함수
def get_image_bytes_from_url(img_url, format="PNG", max_size=(1000, 1000)):
    """
    URL에서 이미지를 가져와 바이트 데이터를 반환합니다.
    """
    try:
        response = requests.get(img_url, timeout=10)
        response.raise_for_status()  # 오류가 있는 응답에 대해 예외 발생
        return get_image_bytes(BytesIO(response.content), format, max_size)
    except Exception as e:
        print(f"URL에서 이미지 가져오기 오류: {e}")
        return None


# 파일 경로에서 이미지를 가져와 바이트 데이터를 얻는 함수
def get_image_bytes_from_file(file_path, format="PNG", max_size=(1000, 1000)):
    """
    파일에서 이미지를 읽어 바이트 데이터를 반환합니다.
    """
    try:
        return get_image_bytes(file_path, format, max_size)
    except Exception as e:
        print(f"파일에서 이미지 읽기 오류: {e}")
        return None


# 바이트 데이터를 PIL.Image 객체로 변환하는 함수
def bytes_to_image(image_bytes: bytes):
    """
    이미지 바이트 데이터를 PIL.Image 객체로 변환합니다.
    """
    return Image.open(BytesIO(image_bytes))


# 이미지 바이트 데이터를 파일로 저장하는 함수
def save_image_bytes(image_bytes: bytes, path: str):
    """
    이미지 바이트 데이터를 파일로 저장합니다.
    """
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, 'wb') as f:
        f.write(image_bytes)


def resize_image(img: Image, width=1280, height=720):
    """
    지정된 크기로 리사이징하는 함수. 
    비율을 유지하면서 이미지를 꽉 채우고, 넘치는 부분은 중앙 기준으로 크롭합니다.
    """
    # 원본 이미지 크기
    orig_width, orig_height = img.size
    
    # 타겟 비율과 원본 비율 계산
    target_ratio = width / height
    orig_ratio = orig_width / orig_height
    
    # 리사이징 크기 계산
    if target_ratio > orig_ratio:
        # 타겟이 더 넓은 경우 - 너비에 맞추고 높이는 크롭
        scale = width / orig_width
        resize_width = width
        resize_height = int(orig_height * scale)
    else:
        # 타겟이 더 좁은 경우 - 높이에 맞추고 너비는 크롭
        scale = height / orig_height
        resize_width = int(orig_width * scale)
        resize_height = height
    
    # 이미지 리사이징
    img = img.resize((resize_width, resize_height), Image.Resampling.LANCZOS)
    
    # 중앙 기준으로 크롭
    left = (resize_width - width) // 2
    top = (resize_height - height) // 2
    right = left + width
    bottom = top + height
    
    # 크롭된 이미지 반환
    return img.crop((left, top, right, bottom))


def create_outpainting_mask(source_image: Image,
                          target_width: int,
                          target_height: int,
                          position: Tuple[float, float] = (0.5, 0.5),
                          size_ratio: float = 1.0):
    """
    Outpainting을 위한 마스크 이미지를 생성합니다.
    
    Args:
        source_image (PIL.Image): 원본 이미지
        target_width (int): 확장하고자 하는 최종 너비
        target_height (int): 확장하고자 하는 최종 높이
        position (Tuple[float, float]): 원본 이미지 배치 위치 비율 (x, y)
                 (0.5, 0.5): 중앙
                 (0.0, 0.0): 좌상단
                 (1.0, 1.0): 우하단
                 (0.0, 0.5): 왼쪽 중앙
        size_ratio (float): target 크기 대비 원본 이미지의 크기 비율 (0.0 < ratio <= 1.0)
                          1.0: target 크기에 맞게 최대한 확장
                          0.5: target 크기의 50%로 조정
                          0.3: target 크기의 30%로 조정
        
    Returns:
        tuple: (확장된 이미지, 마스크 이미지)
        
    Raises:
        ValueError: size_ratio가 0보다 작거나 1보다 큰 경우
    """
    # size_ratio 검증
    if not 0 < size_ratio <= 1.0:
        raise ValueError("size_ratio must be in range (0, 1]")
    
    # 원본 이미지 크기
    src_width, src_height = source_image.size
    
    # target 크기 기준으로 리사이징할 크기 계산
    target_ratio = target_width / target_height
    src_ratio = src_width / src_height
    
    if target_ratio > src_ratio:
        # target이 더 와이드한 경우, 높이 기준으로 조정
        new_height = int(target_height * size_ratio)
        new_width = int(new_height * src_ratio)
    else:
        # target이 더 좁은 경우, 너비 기준으로 조정
        new_width = int(target_width * size_ratio)
        new_height = int(new_width / src_ratio)
    
    # 이미지 리사이징
    source_image = source_image.resize(
        (new_width, new_height),
        Image.Resampling.LANCZOS
    )
    src_width, src_height = new_width, new_height
        
    # 위치 값을 0~1 사이로 클램핑
    pos_x, pos_y = position
    pos_x = max(0.0, min(1.0, pos_x))
    pos_y = max(0.0, min(1.0, pos_y))
    
    # 원본 이미지가 들어갈 영역은 흰색으로 채움
    # 실제 픽셀 좌표 계산
    paste_x = int((target_width - src_width) * pos_x)
    paste_y = int((target_height - src_height) * pos_y)
    
    # 확장된 이미지 생성
    BLACK = (255, 255, 255)
    WHITE = (0, 0, 0)
    extended_image = Image.new("RGB", (target_width, target_height), BLACK)
    extended_image.paste(source_image, (paste_x, paste_y))
    
    # 마스크 이미지 생성
    mask_image = Image.new("RGB", (target_width, target_height), BLACK)
    original_image_shape = Image.new(
        "RGB", (src_width, src_height), WHITE
    )
    mask_image.paste(original_image_shape, (paste_x, paste_y))
     
    return extended_image, mask_image


def get_thumbnail(video_bytes: str, timestamp: int = 0):
    video_buffer = io.BytesIO(video_bytes)
    container = av.open(video_buffer)
    stream = container.streams.video[0]

    fps = stream.average_rate
    target_frame = int(timestamp * float(fps))

    container.seek(target_frame, stream=stream)

    for frame in container.decode(video=0):
        img = frame.to_image()

        img_byte_arr = io.BytesIO()
        img.save(img_byte_arr, format='JPEG', quality=90)
        img_byte_arr.seek(0)
        return img_byte_arr.getvalue()

    return None