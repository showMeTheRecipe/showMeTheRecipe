import time
import boto3
from botocore.exceptions import ClientError

def transcribe_audio(job_name, job_uri, region_name):
    transcribe = boto3.client('transcribe', region_name=region_name)
     
    try:
        print(transcribe)
        transcribe.start_transcription_job(
            TranscriptionJobName=job_name,
            Media={'MediaFileUri': job_uri},
            MediaFormat='mp3',
            LanguageCode='ko-KR',
            OutputBucketName='showmetherecipe-bucket'  # 트랜스크립션 결과를 저장할 버킷 지정
        )
        
        while True:
            status = transcribe.get_transcription_job(TranscriptionJobName=job_name)
            if status['TranscriptionJob']['TranscriptionJobStatus'] in ['COMPLETED', 'FAILED']:
                break
            print("Transcription job in progress...")
            time.sleep(5)
        
        if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            return status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            
        else:
            print(f"Transcription job failed: {status['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
            return None
    
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None

def text_to_speech(text, output_file, region_name):
    polly = boto3.client('polly', region_name=region_name)
    
    try:
        response = polly.synthesize_speech(
            Text=text,
            OutputFormat='mp3',
            VoiceId='Seoyeon'  # 한국어 여성 음성
        )

        # 음성 파일 저장
        if "AudioStream" in response:
            with open(output_file, 'wb') as file:
                file.write(response['AudioStream'].read())
            print(f"Audio content written to file {output_file}")
            return output_file
        else:
            print("Could not stream audio")
            return None

    except ClientError as e:
        print(f"An error occurred: {e}")
        return None

def process_recipe(recipe_text, region_name):
    # 레시피 텍스트를 단계별로 분리
    steps = recipe_text.split('\n')
    audio_files = []

    for i, step in enumerate(steps):
        if step.strip():  # 빈 줄 제외
            output_file = f'step_{i+1}.mp3'
            result = text_to_speech(step, output_file, region_name)
            if result:
                audio_files.append(result)

    return audio_files

# 사용 예시
if __name__ == "__main__":
    region_name = 'ap-northeast-2'  # 여기에 사용하는 AWS 리전을 입력하세요
    job_name = 'test-transcription-job'
    job_uri = 's3://your-bucket-name/your-audio-file.mp3'

    # 오디오 파일 트랜스크립션
    transcript_uri = transcribe_audio(job_name, job_uri, region_name)
    
    if transcript_uri:
        # 트랜스크립션 결과를 가져와서 텍스트 추출 (이 부분은 구현 필요)
        recipe_text = "여기에 트랜스크립션 결과 텍스트가 들어갑니다."
        
        # 레시피 텍스트를 음성으로 변환
        audio_files = process_recipe(recipe_text, region_name)
        print(f"생성된 오디오 파일: {audio_files}")
    else:
        print("트랜스크립션 실패")