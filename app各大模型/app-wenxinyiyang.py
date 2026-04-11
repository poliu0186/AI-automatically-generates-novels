from flask import Flask, request, Response, render_template
import requests
import json
import logging
import os
from typing import Generator
import time

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# 文心一言API配置
API_KEY = os.environ.get('WENXIN_API_KEY', '')  # Set via environment variable
SECRET_KEY = os.environ.get('WENXIN_SECRET_KEY', '')  # Set via environment variable

def get_access_token() -> str:
    """
    获取百度API access token
    """
    url = "https://aip.baidubce.com/oauth/2.0/token"
    params = {
        "grant_type": "client_credentials",
        "client_id": API_KEY,
        "client_secret": SECRET_KEY
    }
    try:
        response = requests.post(url, params=params)
        response.raise_for_status()
        return response.json().get("access_token")
    except Exception as e:
        app.logger.error(f"获取access token失败: {e}")
        raise

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gen', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    app.logger.debug(f"收到prompt请求: {prompt}")
    
    def generate_stream() -> Generator[str, None, None]:
        try:
            # 获取access token
            access_token = get_access_token()
            
            # 调用文心一言API
            url = f"https://aip.baidubce.com/rpc/2.0/ai_custom/v1/wenxinworkshop/chat/completions?access_token={access_token}"
            
            headers = {
                "Content-Type": "application/json"
            }
            
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "stream": True
            }
            
            response = requests.post(url, headers=headers, json=payload, stream=True)
            response.raise_for_status()
            
            app.logger.debug("成功创建流式响应")
            
            for line in response.iter_lines():
                if line:
                    line = line.decode('utf-8')
                    if line.startswith('data: '):
                        line = line[6:]
                    
                    if line.strip() == '[DONE]':
                        break
                        
                    try:
                        chunk = json.loads(line)
                        if 'error_code' in chunk:
                            error_msg = chunk.get('error_msg', '未知错误')
                            app.logger.error(f"API错误: {error_msg}")
                            yield f"错误: {error_msg}"
                            break
                        
                        if content := chunk.get('result', ''):
                            app.logger.debug(f"输出内容: {content}")
                            yield content
                            
                    except json.JSONDecodeError as e:
                        app.logger.error(f"JSON解析错误: {e}")
                        continue
                        
        except requests.exceptions.RequestException as e:
            app.logger.error(f"请求错误: {e}")
            yield f"错误: {str(e)}"
        except Exception as e:
            app.logger.error(f"意外错误: {e}")
            yield f"错误: {str(e)}"
    
    return Response(generate_stream(), mimetype='text/plain')

@app.route('/gen2', methods=['POST'])
def generate2():
    """
    第二个生成接口，使用相同的实现
    可以根据需要修改参数或模型
    """
    return generate()

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true'), port=60000, host="0.0.0.0")
