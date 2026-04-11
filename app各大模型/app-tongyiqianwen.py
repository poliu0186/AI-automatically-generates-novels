
from flask import Flask, request, Response, render_template
import dashscope
import json
import logging
import os
from http import HTTPStatus

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# API Configurations
API_KEY_1 = os.environ.get('DASHSCOPE_API_KEY', '')  # Set via environment variable
API_KEY_2 = os.environ.get('DASHSCOPE_API_KEY_2', API_KEY_1)

# 设置通义千问API密钥
dashscope.api_key = API_KEY_1

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
            response = dashscope.Generation.call(
                model='qwen-max',  # 或 'qwen-plus', 'qwen-turbo'
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                result_format='message',
                stream=True,
                temperature=0.7,
                top_p=0.95,
                max_tokens=1500,
                stop=None,
                repetition_penalty=1.0,
                top_k=None,
                enable_search=False,
                incremental_output=True
            )
            
            app.logger.debug("Stream created successfully for gen")
            
            for chunk in response:
                if chunk.status_code == HTTPStatus.OK:
                    if hasattr(chunk.output, 'choices') and \
                       len(chunk.output.choices) > 0 and \
                       hasattr(chunk.output.choices[0], 'message') and \
                       'content' in chunk.output.choices[0].message:
                        content = chunk.output.choices[0].message['content']
                        app.logger.debug(f"Yielding chunk: {content}")
                        yield content
                else:
                    error_msg = f"Error: {chunk.code} {chunk.message}"
                    app.logger.error(error_msg)
                    yield error_msg
                    
        except Exception as e:
            app.logger.error(f"Error in generate_stream: {e}")
            yield f"Error: {str(e)}"
    
    return Response(generate_stream(), mimetype='text/plain')

@app.route('/gen2', methods=['POST'])
def generate2():
    data = request.json
    prompt = data.get('prompt', '')
    app.logger.debug(f"Received prompt for gen2: {prompt}")
    
    # 临时切换到第二个API密钥
    original_api_key = dashscope.api_key
    dashscope.api_key = API_KEY_2
    
    def generate_stream():
        try:
            response = dashscope.Generation.call(
                model='qwen-turbo',  # 使用较轻量的模型
                messages=[{
                    "role": "user",
                    "content": prompt
                }],
                result_format='message',
                stream=True,
                temperature=0.8,  # 可以调整参数
                top_p=0.95,
                max_tokens=1500,
                stop=None,
                repetition_penalty=1.0,
                top_k=None,
                enable_search=False,
                incremental_output=True
            )
            
            app.logger.debug("Stream created successfully for gen2")
            
            for chunk in response:
                if chunk.status_code == HTTPStatus.OK:
                    if hasattr(chunk.output, 'choices') and \
                       len(chunk.output.choices) > 0 and \
                       hasattr(chunk.output.choices[0], 'message') and \
                       'content' in chunk.output.choices[0].message:
                        content = chunk.output.choices[0].message['content']
                        app.logger.debug(f"Yielding chunk: {content}")
                        yield content
                else:
                    error_msg = f"Error: {chunk.code} {chunk.message}"
                    app.logger.error(error_msg)
                    yield error_msg
                    
        except Exception as e:
            app.logger.error(f"Error in generate_stream: {e}")
            yield f"Error: {str(e)}"
        finally:
            # 恢复原始API密钥
            dashscope.api_key = original_api_key
    
    return Response(generate_stream(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true'), port=60000, host="0.0.0.0")
