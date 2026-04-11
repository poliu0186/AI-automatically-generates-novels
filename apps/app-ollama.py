from flask import Flask, request, Response, render_template
import requests
import json
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# API Configurations
API_ENDPOINT = 'http://127.0.0.1:11434/api/generate'
MODEL_NAME = 'qwen2.5:14b'

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
            # Prepare the request payload for Ollama
            payload = {
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": True
            }
            
            # Make streaming request to Ollama
            response = requests.post(
                API_ENDPOINT,
                json=payload,
                stream=True
            )
            
            app.logger.debug("Stream created successfully for gen")
            
            # Process the streaming response
            for line in response.iter_lines():
                if line:
                    json_response = json.loads(line)
                    if 'response' in json_response:
                        content = json_response['response']
                        app.logger.debug(f"Yielding chunk: {content}")
                        yield content
                        
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
            # Prepare the request payload for Ollama
            payload = {
                "model": MODEL_NAME,
                "prompt": prompt,
                "stream": True
            }
            
            # Make streaming request to Ollama
            response = requests.post(
                API_ENDPOINT,
                json=payload,
                stream=True
            )
            
            app.logger.debug("Stream created successfully for gen2")
            
            # Process the streaming response
            for line in response.iter_lines():
                if line:
                    json_response = json.loads(line)
                    if 'response' in json_response:
                        content = json_response['response']
                        app.logger.debug(f"Yielding chunk: {content}")
                        yield content
                        
        except Exception as e:
            app.logger.error(f"Error in generate_stream: {e}")
            yield f"Error: {str(e)}"
    
    return Response(generate_stream(), mimetype='text/plain')

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true'), port=60000, host="0.0.0.0")
