import yt_dlp
import boto3
import os

# AWS S3 설정
s3_client = boto3.client('s3', region_name='ap-northeast-2')
BUCKET_NAME = 'showmetherecipe-bucket'

def download_audio_from_youtube(url, output_path='audio.mp3'):
    """유튜브에서 오디오를 다운로드하여 로컬 파일로 저장하는 함수."""
    try:
        ydl_opts = {
            'format': 'bestaudio/best',
            'outtmpl': output_path,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
            'username': 'oauth2',
            'password': '',  # OAuth2 사용 시 빈 문자열로 설정
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        print(f"Audio downloaded successfully to {output_path}")
    except Exception as e:
        print(f"Error downloading audio: {e}")

def upload_to_s3(file_path, bucket_name, s3_file_key):
    """로컬 파일을 S3에 업로드하는 함수."""
    try:
        s3_client.upload_file(file_path, bucket_name, s3_file_key)
        print(f"File uploaded successfully to S3 with key {s3_file_key}")
    except Exception as e:
        print(f"Error uploading file to S3: {e}")

# 위의 함수들을 app.py에서 호출할 것이기 때문에 아래의 main 블록은 필요하지 않음