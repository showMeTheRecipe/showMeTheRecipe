from flask import Flask, request, jsonify, render_template
import boto3
import json
import os
import uuid
from dotenv import load_dotenv
from transcribe_audio import transcribe_audio
from youtube_video_down import download_audio_from_youtube, upload_to_s3

app = Flask(__name__)

# AWS 서비스 클라이언트 생성
s3 = boto3.client('s3', region_name='ap-northeast-2')
polly = boto3.client('polly', region_name='ap-northeast-2')
bedrock_client = boto3.client('bedrock-runtime', region_name='us-east-1')

load_dotenv()

BUCKET_NAME = 'showmetherecipe-bucket'
REGION_NAME = 'ap-northeast-2'

def generate_s3_url(bucket_name, s3_key, region):
    url = f"https://{bucket_name}.s3.{region}.amazonaws.com/{s3_key}"
    return url

def download_file_from_s3(bucket_name, s3_key, local_path):
    """S3에서 파일 다운로드"""
    s3.download_file(bucket_name, s3_key, local_path)

def upload_file_to_s3(local_path, bucket_name, s3_key):
    """로컬 파일을 S3에 업로드"""
    with open(local_path, 'rb') as data:
        s3.upload_fileobj(data, bucket_name, s3_key)

def read_text_from_file(file_path):
    """파일에서 텍스트 읽기"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()

def decode_unicode_escape(text):
    """텍스트의 Unicode 이스케이프 시퀀스를 디코딩"""
    return text.encode('utf-8').decode('unicode_escape')

def clean_text(text):
    """텍스트에서 특수 문자 및 불필요한 공백 제거"""
    return text.strip()

def synthesize_speech(text, output_format='mp3', voice_id='Seoyeon'):
    """텍스트를 음성으로 변환 (한국어 설정)"""
    response = polly.synthesize_speech(
        Text=text,
        OutputFormat=output_format,
        VoiceId=voice_id,
        LanguageCode='ko-KR'  # 한국어
    )
    return response['AudioStream'].read()

def save_audio_to_local(audio_stream, local_path):
    """음성 파일을 로컬에 저장"""
    with open(local_path, 'wb') as file:
        file.write(audio_stream)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/extract_recipe', methods=['POST'])
def extract_recipe():
    video_url = request.form['video_url']
    
    try:
        local_audio_path = "/home/ec2-user/environment/hohoit.mp3"
        s3_audio_key = f"audio/{uuid.uuid4()}.mp3"
        
        # 다운로드 및 업로드
        download_audio_from_youtube(video_url, local_audio_path)
        upload_file_to_s3(local_audio_path, BUCKET_NAME, s3_audio_key)
        os.unlink(local_audio_path)
        
        s3_url = generate_s3_url(BUCKET_NAME, s3_audio_key, REGION_NAME)
        job_name = f"transcribe-{uuid.uuid4()}"
        transcript_uri = transcribe_audio(job_name, s3_url, REGION_NAME)
        
        if not transcript_uri:
            return jsonify({'success': False, 'error': 'Transcription failed'})
        
        transcript_key = transcript_uri.split('/')[-1]
        response = s3.get_object(Bucket=BUCKET_NAME, Key=transcript_key)
        transcript_text = json.loads(response['Body'].read().decode('utf-8'))['results']['transcripts'][0]['transcript']
        
        # Prepare the prompt for Bedrock using the updated structure
        prompt = (
            f"다음 텍스트에서 정보를 추출하십시오:\n\n"
            f"1. **레시피 이름:** <추출된 레시피 이름>\n"
            f"2. **재료:** <재료 목록>\n"
            f"3. **조리 방법:** <조리 방법>\n\n"
            f"텍스트: {transcript_text}\n\n"
            f"다음 형식으로 정보를 응답하십시오:\n\n"
            f"레시피 이름: <추출된 레시피 이름>\n"
            f"재료:\n - <재료 1> (<일반적인 일인분 중량>g, 약 <칼로리> 칼로리)\n"
            f" - <재료 2> (<일반적인 일인분 중량>g, 약 <칼로리> 칼로리)\n"
            f" - (각 재료에 대하여 계속...)\n"
            f" 전체 칼로리: <전체 칼로리>\n"
            f"조리 방법:\n  1.<단계 1>\n 2.<단계 2>\n - (각 단계에 대하여 계속...)"
        )
        
        body = json.dumps({
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "messages": [{
                "role": "user",
                "content": [{"type": "text", "text": prompt}]
            }],
        })
        
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=body,
        )
        response_body = json.loads(response['body'].read())
        recipe = response_body['content'][0]['text']
        
        # Save recipe to S3
        json_string = json.dumps(recipe, ensure_ascii=False)  # Ensure non-ASCII characters are not escaped
        recipe_file_name = f"llm_recipe/{uuid.uuid4()}.txt"
        s3.put_object(Bucket=BUCKET_NAME, Key=recipe_file_name, Body=json_string, ContentType='application/txt')
        
        audio_stream = synthesize_speech(recipe)
        
        local_audio_path = 'converted_audio.mp3'
        save_audio_to_local(audio_stream, local_audio_path)
        audio_s3_key = f'audio_recipes/{uuid.uuid4()}.mp3'
        upload_file_to_s3(local_audio_path, BUCKET_NAME, audio_s3_key)
        
        return jsonify({'success': True, 'recipe': recipe, 'audio_s3_key': audio_s3_key})
    
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
