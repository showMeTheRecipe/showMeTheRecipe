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
        ## print(status['TranscriptionJob']['TranscriptionJobStatus'])
        if status['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED':
            return status['TranscriptionJob']['Transcript']['TranscriptFileUri']
            
        else:
            print(f"Transcription job failed: {status['TranscriptionJob'].get('FailureReason', 'Unknown error')}")
            return None
    
    except ClientError as e:
        print(f"An error occurred: {e}")
        return None
        
        
