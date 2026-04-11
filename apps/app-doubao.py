from flask import Flask, request, Response, render_template
from openai import OpenAI
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# API Configurations
API_ENDPOINT_1 = os.environ.get('DOUBAO_API_ENDPOINT', 'https://api.doubao.com/v1')
API_KEY_1 = os.environ.get('DOUBAO_API_KEY', '')  # Set via environment variable
API_ENDPOINT_2 = os.environ.get('DOUBAO_API_ENDPOINT_2', API_ENDPOINT_1)
API_KEY_2 = os.environ.get('DOUBAO_API_KEY_2', API_KEY_1)

# Initialize OpenAI-compatible clients
client1 = OpenAI(
    base_url=API_ENDPOINT_1,
    api_key=API_KEY_1,
    default_headers={
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
)

client2 = OpenAI(
    base_url=API_ENDPOINT_2,
    api_key=API_KEY_2,
    default_headers={
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
    }
)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gen', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    app.logger.debug(f"Received prompt for gen: {prompt}")
    
    def generate_stream():
        try:
            completion = client1.chat.completions.create(
                model="doubao-text-v1",  # 豆包模型名称
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                stream=True,
                temperature=0.7,
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                max_tokens=4096
            )
            
            app.logger.debug("Stream created successfully for gen")
            
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    app.logger.debug(f"Yielding chunk: {chunk.choices[0].delta.content}")
                    yield chunk.choices[0].delta.content
                    
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
            completion = client2.chat.completions.create(
                model="doubao-text-v1",  # 可以使用不同的模型版本
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                stream=True,
                temperature=0.8,  # 可以调整参数
                top_p=0.95,
                frequency_penalty=0,
                presence_penalty=0,
                max_tokens=4096
            )
            
            app.logger.debug("Stream created successfully for gen2")
            
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    app.logger.debug(f"Yielding chunk: {chunk.choices[0].delta.content}")
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            app.logger.error(f"Error in generate_stream: {e}")
            yield f"Error: {str(e)}"
    
    return Response(generate_stream(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true'), port=60000, host="0.0.0.0")
