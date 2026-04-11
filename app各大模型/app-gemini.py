from flask import Flask, request, Response, render_template
import google.generativeai as genai
import json
import logging
import os
import requests
import urllib3
import time
import sys
import traceback
from datetime import datetime, timedelta
from collections import deque

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

if os.environ.get('HTTPS_PROXY'):
    pass  # Use proxy from environment
elif os.environ.get('GEMINI_HTTPS_PROXY'):
    os.environ['HTTPS_PROXY'] = os.environ['GEMINI_HTTPS_PROXY']
    os.environ['HTTP_PROXY'] = os.environ.get('GEMINI_HTTP_PROXY', os.environ['GEMINI_HTTPS_PROXY'])

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

class TokenStats:
    def __init__(self):
        self.total_tokens = 1000000
        self.remaining_tokens = 1000000
        self.daily_limit = 10000
        self.monthly_limit = 200000
        self.today_calls = 0
        self.month_calls = 0
        self.last_call_time = None
        self.response_times = deque(maxlen=100)
        self.success_count = 0
        self.total_count = 0
        self.token_usages = deque(maxlen=100)
        self.last_reset_day = datetime.now().day
        self.last_reset_month = datetime.now().month

    def reset_daily(self):
        current_day = datetime.now().day
        if current_day != self.last_reset_day:
            self.today_calls = 0
            self.last_reset_day = current_day

    def reset_monthly(self):
        current_month = datetime.now().month
        if current_month != self.last_reset_month:
            self.month_calls = 0
            self.last_reset_month = current_month

    def record_call(self, success=True, response_time=0, tokens_used=0):
        self.reset_daily()
        self.reset_monthly()
        
        self.last_call_time = datetime.now()
        self.today_calls += 1
        self.month_calls += 1
        self.total_count += 1
        
        if success:
            self.success_count += 1
        
        self.response_times.append(response_time)
        if tokens_used > 0:
            self.token_usages.append(tokens_used)
            self.remaining_tokens = max(0, self.remaining_tokens - tokens_used)

    @property
    def avg_response_time(self):
        return sum(self.response_times) / len(self.response_times) if self.response_times else 0

    @property
    def success_rate(self):
        return self.success_count / self.total_count if self.total_count > 0 else 1.0

    @property
    def avg_token_usage(self):
        return int(sum(self.token_usages) / len(self.token_usages)) if self.token_usages else 0

    def to_dict(self):
        return {
            "remaining_tokens": self.remaining_tokens,
            "total_tokens": self.total_tokens,
            "today_calls": self.today_calls,
            "daily_limit": self.daily_limit,
            "month_calls": self.month_calls,
            "monthly_limit": self.monthly_limit,
            "last_call_time": self.last_call_time.isoformat() if self.last_call_time else None,
            "avg_response_time": self.avg_response_time,
            "success_rate": self.success_rate,
            "avg_token_usage": self.avg_token_usage
        }

token_stats = TokenStats()

def trigger_smart_placement():
    try:
        us_urls = [
            'https://www.google.com',
            'https://cloud.google.com',
            'https://ai.google.dev'
        ]
        
        for url in us_urls:
            try:
                start_time = time.time()
                response = requests.get(url, timeout=5, verify=False)
                response_time = (time.time() - start_time) * 1000
                
                if response.status_code == 200:
                    token_stats.record_call(success=True, response_time=response_time)
                    app.logger.info(f"Successfully connected to {url}")
                    time.sleep(1)
                    return True
                else:
                    token_stats.record_call(success=False, response_time=response_time)
            except Exception as e:
                app.logger.warning(f"Failed to connect to {url}: {str(e)}")
                token_stats.record_call(success=False, response_time=5000)
                continue
                
        return False
    except Exception as e:
        app.logger.error(f"Error in trigger_smart_placement: {str(e)}")
        return False

GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY', '')  # Set via environment variable
genai.configure(api_key=GOOGLE_API_KEY)

def init_api():
    try:
        if not trigger_smart_placement():
            app.logger.warning("Failed to trigger smart-placement")
        
        start_time = time.time()
        models = genai.list_models()
        response_time = (time.time() - start_time) * 1000
        
        token_stats.record_call(success=True, response_time=response_time)
        app.logger.info(f"Available models: {[model.name for model in models]}")
        return True
    except Exception as e:
        app.logger.error(f"Error during API initialization: {str(e)}")
        token_stats.record_call(success=False, response_time=5000)
        return False

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gen', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    app.logger.debug(f"Received prompt for gen: {prompt}")
    
    def generate_stream():
        max_retries = 5
        retry_count = 0
        retry_delay = 1
        
        while retry_count < max_retries:
            try:
                start_time = time.time()
                model = genai.GenerativeModel('gemini-exp-1206')
                
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.7,
                        top_p=0.95,
                        max_output_tokens=4096
                    ),
                    stream=True
                )
                
                total_tokens = 0
                for chunk in response:
                    if chunk.text:
                        app.logger.debug(f"Yielding chunk: {chunk.text}")
                        total_tokens += len(chunk.text.split())
                        yield chunk.text
                
                response_time = (time.time() - start_time) * 1000
                token_stats.record_call(success=True, response_time=response_time, tokens_used=total_tokens)
                break
                        
            except Exception as e:
                retry_count += 1
                error_msg = f"Error in generate (attempt {retry_count}/{max_retries}): {str(e)}"
                app.logger.error(error_msg)
                token_stats.record_call(success=False, response_time=5000)
                
                if retry_count >= max_retries:
                    yield f"生成失败（已重试{retry_count}次）。错误信息：{str(e)}\n建议：\n1. 请稍后重试\n2. 尝试简化或修改提示词\n3. 如果问题持续，请联系管理员"
                else:
                    retry_delay = min(retry_delay * 2, 8)
                    time.sleep(retry_delay)
                    yield f"正在重试 ({retry_count}/{max_retries})...\n"
                    continue
    
    return Response(generate_stream(), mimetype='text/plain')

@app.route('/gen2', methods=['POST'])
def generate2():
    data = request.json
    prompt = data.get('prompt', '')
    app.logger.debug(f"Received prompt for gen2: {prompt}")
    
    def generate_stream():
        max_retries = 5
        retry_count = 0
        retry_delay = 1
        
        while retry_count < max_retries:
            try:
                start_time = time.time()
                model = genai.GenerativeModel('gemini-exp-1206')
                
                response = model.generate_content(
                    prompt,
                    generation_config=genai.types.GenerationConfig(
                        temperature=0.8,
                        top_p=0.92,
                        max_output_tokens=4096
                    ),
                    stream=True
                )
                
                total_tokens = 0
                for chunk in response:
                    if chunk.text:
                        app.logger.debug(f"Yielding chunk: {chunk.text}")
                        total_tokens += len(chunk.text.split())
                        yield chunk.text
                
                response_time = (time.time() - start_time) * 1000
                token_stats.record_call(success=True, response_time=response_time, tokens_used=total_tokens)
                break
                        
            except Exception as e:
                retry_count += 1
                error_msg = f"Error in generate2 (attempt {retry_count}/{max_retries}): {str(e)}"
                app.logger.error(error_msg)
                token_stats.record_call(success=False, response_time=5000)
                
                if retry_count >= max_retries:
                    yield f"生成失败（已重试{retry_count}次）。错误信息：{str(e)}\n建议：\n1. 请稍后重试\n2. 尝试简化或修改提示词\n3. 如果问题持续，请联系管理员"
                else:
                    retry_delay = min(retry_delay * 2, 8)
                    time.sleep(retry_delay)
                    yield f"正在重试 ({retry_count}/{max_retries})...\n"
                    continue
    
    return Response(generate_stream(), mimetype='text/plain')

@app.route('/api-info')
def api_info():
    try:
        info = {
            "models": [],
            "current_model": {
                "name": "gemini-exp-1206",
                "details": None
            },
            "system_info": {
                "python_version": sys.version,
                "genai_version": genai.__version__
            },
            "token_info": token_stats.to_dict()
        }
        
        models = genai.list_models()
        for model in models:
            model_info = {
                "name": model.name,
                "display_name": model.display_name,
                "description": model.description,
                "generation_methods": [method for method in dir(model) if not method.startswith('_')],
                "supported_generation_methods": model.supported_generation_methods,
                "temperature_range": {"min": 0.0, "max": 1.0},
                "top_p_range": {"min": 0.0, "max": 1.0},
                "top_k_range": {"min": 1, "max": 40},
                "max_output_tokens": 4096,
            }
            info["models"].append(model_info)
            
            if model.name == "models/gemini-exp-1206":
                info["current_model"]["name"] = model.name
                info["current_model"]["details"] = model_info
        
        return Response(
            json.dumps(info, indent=2, ensure_ascii=False),
            mimetype='application/json'
        )
        
    except Exception as e:
        error_info = {
            "error": str(e),
            "traceback": "See server logs for details."
        }
        return Response(
            json.dumps(error_info, indent=2, ensure_ascii=False),
            status=500,
            mimetype='application/json'
        )

@app.route('/api-dashboard')
def api_dashboard():
    return render_template('api-info.html')

if __name__ == '__main__':
    if init_api():
        app.run(debug=os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true'), port=60000, host="0.0.0.0")
    else:
        app.logger.error("Failed to initialize API, service will not start")  