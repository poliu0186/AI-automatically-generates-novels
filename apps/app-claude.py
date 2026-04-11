from flask import Flask, request, Response, render_template
import requests
import json
import logging
import os
from typing import Generator

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# API Configurations
API_ENDPOINT_1 = os.environ.get('CLAUDE_API_ENDPOINT', 'https://api.anthropic.com/v1/messages')
API_KEY_1 = os.environ.get('CLAUDE_API_KEY', '')  # Set via environment variable
API_ENDPOINT_2 = os.environ.get('CLAUDE_API_ENDPOINT_2', API_ENDPOINT_1)
API_KEY_2 = os.environ.get('CLAUDE_API_KEY_2', API_KEY_1)

def create_headers(api_key: str) -> dict:
    return {
        'x-api-key': api_key,
        'anthropic-version': '2023-06-01',
        'content-type': 'application/json',
        'accept': 'text/event-stream'
    }

@app.route('/')
def index():
    return render_template('index.html')

def process_claude_stream(response: requests.Response) -> Generator[str, None, None]:
    for line in response.iter_lines():
        if not line:
            continue
            
        try:
            if line.startswith(b'data: '):
                data_str = line[6:].decode('utf-8')
                if data_str.strip() == '[DONE]':
                    break
                    
                data = json.loads(data_str)
                if data['type'] == 'message_delta':
                    if text_delta := data.get('delta', {}).get('text', ''):
                        yield text_delta
                
        except json.JSONDecodeError as e:
            app.logger.error(f"JSON decode error: {e}")
            continue
        except Exception as e:
            app.logger.error(f"Error processing stream: {e}")
            continue

@app.route('/gen', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    app.logger.debug(f"Received prompt for gen: {prompt}")
    
    def generate_stream():
        try:
            # Claude API payload structure
            payload = {
                "model": "claude-3-sonnet-20240229",  # 或选择其他 Claude 模型
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": True,
                "max_tokens": 4096,
                "temperature": 0.7
            }
            
            response = requests.post(
                API_ENDPOINT_1,
                headers=create_headers(API_KEY_1),
                json=payload,
                stream=True
            )
            
            if response.status_code != 200:
                error_message = f"API Error: {response.status_code} - {response.text}"
                app.logger.error(error_message)
                yield error_message
                return
                
            app.logger.debug("Stream created successfully for gen")
            
            for chunk in process_claude_stream(response):
                app.logger.debug(f"Yielding chunk: {chunk}")
                yield chunk
                
        except Exception as e:
            app.logger.error(f"Error in generate_stream: {e}")
            yield f"Error: {str(e)}"
    
    return Response(generate_stream(), mimetype='text/plain')

@app.route('/gen2', methods=['POST'])
def generate2():
    data = request.json
    prompt = data.get('prompt', '')
    app.logger.debug(f"Received prompt for gen2: {prompt}")
    
    def generate_stream():
        try:
            # 可以为 gen2 配置不同的参数
            payload = {
                "model": "claude-3-haiku-20240307",  # 使用不同的模型或参数
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "stream": True,
                "max_tokens": 4096,
                "temperature": 0.8,  # 可以调整温度
            }
            
            response = requests.post(
                API_ENDPOINT_2,
                headers=create_headers(API_KEY_2),
                json=payload,
                stream=True
            )
            
            if response.status_code != 200:
                error_message = f"API Error: {response.status_code} - {response.text}"
                app.logger.error(error_message)
                yield error_message
                return
                
            app.logger.debug("Stream created successfully for gen2")
            
            for chunk in process_claude_stream(response):
                app.logger.debug(f"Yielding chunk: {chunk}")
                yield chunk
                
        except Exception as e:
            app.logger.error(f"Error in generate_stream: {e}")
            yield f"Error: {str(e)}"
    
    return Response(generate_stream(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true'), port=60000, host="0.0.0.0")
