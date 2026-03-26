from flask import Flask, request, Response, render_template
from openai import OpenAI
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# API Configurations
API_ENDPOINT_1 = 'https://open.bigmodel.cn/api/paas/v4/'
API_KEY_1 = '7e680b473d4f40e58b5bae0fe43ee3ce.Q7sWfbxYQVFcjHUz'  # 请替换为您的智谱AI API Key

API_ENDPOINT_2 = 'https://open.bigmodel.cn/api/paas/v4/'
API_KEY_2 = '7e680b473d4f40e58b5bae0fe43ee3ce.Q7sWfbxYQVFcjHUz'  # 请替换为您的智谱AI API Key

# Initialize OpenAI clients
client1 = OpenAI(
    base_url=API_ENDPOINT_1,
    api_key=API_KEY_1
)

client2 = OpenAI(
    base_url=API_ENDPOINT_2,
    api_key=API_KEY_2
)

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/bingte')
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
                model="glm-4.5-air",  # GLM-4.6v 视觉模型
                messages=[{"role": "user", "content": prompt}],
                stream=True
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
                model="glm-4.5-air",  # GLM-4 文本模型
                messages=[{"role": "user", "content": prompt}],
                stream=True
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
    app.run(debug=True, port=60001, host="0.0.0.0")
