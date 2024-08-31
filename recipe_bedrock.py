from flask import Flask, request, jsonify
import boto3
import json
import os
from dotenv import load_dotenv

app = Flask(__name__)

# .env 파일이 있으면 로드 (Cloud9 환경에서는 필요 없을 수 있음)
load_dotenv()

# AWS SDK for Python (Boto3) 클라이언트 초기화
bedrock_client = boto3.client(
    'bedrock-runtime', 
    region_name='us-east-1' # AWS 리전
    # Cloud9에서는 AWS 자격 증명을 따로 지정할 필요 없음
)


# ChatGPT에 요청을 보내는 엔드포인트
@app.route('/chat', methods=['POST'])
def chat():
    user_input = request.json.get('message', '')
    
    if not user_input:
        return jsonify({'error': 'No input message provided'}), 400
    
    prompt = (
        f"다음 텍스트에서 정보를 추출하십시오:\n\n"
        f"1. **레시피 이름:** <추출된 레시피 이름>\n"
        f"2. **재료:** <재료 목록>\n"
        f"3. **조리 방법:** <조리 방법>\n\n"
        f"텍스트: {user_input}\n\n"
        f"다음 형식으로 정보를 응답하십시오:\n\n"
        f"레시피 이름: <추출된 레시피 이름>\n"
        f"재료:\n - <재료 1> (<일반적인 일인분 중량>g, 약 <칼로리> 칼로리)\n"
        f" - <재료 2> (<일반적인 일인분 중량>g, 약 <칼로리> 칼로리)\n"
        f" - (각 재료에 대하여 계속...)\n"
        f" 전체 칼로리: <전체 칼로리>"
        f"조리 방법:\n - <단계 1>\n - <단계 2>\n - (각 단계에 대하여 계속...)"
    )

    try:
        # Bedrock에 요청 보내기
        body = json.dumps(
            {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 1000,
                "messages": [{
                    "role": "user",
                    "content": [{"type": "text", "text": prompt}]
                }],
            }
        )
        
        response = bedrock_client.invoke_model(
            modelId="anthropic.claude-3-sonnet-20240229-v1:0",
            body=body,
        )
        response_body = json.loads(response.get("body").read())
        output_text = response_body["content"][0]["text"]
    
        
        return jsonify({'response': output_text})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    # Cloud9에서는 0.0.0.0으로 호스트를 설정하여 외부 접근 허용
    app.run(debug=True, host='0.0.0.0')
