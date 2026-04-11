from flask import Flask, request, Response, render_template
import openai
import json
import logging
import os

app = Flask(__name__)
logging.basicConfig(level=logging.DEBUG)

# OpenAI API configuration
openai.api_key = os.environ.get("OPENAI_API_KEY", "")  # Set via environment variable
OPENAI_MODEL = os.environ.get("OPENAI_MODEL", "gpt-3.5-turbo")

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/gen', methods=['POST'])
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    api_key = openai.api_key  # API key must be set server-side, not from client
    model = data.get('model', OPENAI_MODEL)
    
    app.logger.debug(f"Received prompt: {prompt}")

    def generate_stream():
        try:
            # Create messages format required by OpenAI
            messages = [{"role": "user", "content": prompt}]
            
            # Make API call with streaming
            response = openai.ChatCompletion.create(
                model=model,
                messages=messages,
                stream=True,
                api_key=api_key
            )

            app.logger.debug("Started streaming from OpenAI")

            for chunk in response:
                if chunk and chunk.choices and chunk.choices[0].delta.get('content'):
                    content = chunk.choices[0].delta.content
                    # Format response to match original format
                    response_chunk = {
                        "response": content
                    }
                    app.logger.debug(f"Yielding response: {content}")
                    yield json.dumps(response_chunk) + '\n'

        except openai.error.OpenAIError as e:
            error_response = {
                "error": str(e),
                "response": f"Error: {str(e)}"
            }
            app.logger.error(f"OpenAI API error: {e}")
            yield json.dumps(error_response) + '\n'
            
        except Exception as e:
            error_response = {
                "error": str(e),
                "response": f"Error: {str(e)}"
            }
            app.logger.error(f"General error: {e}")
            yield json.dumps(error_response) + '\n'

    return Response(generate_stream(), mimetype='application/x-ndjson')

if __name__ == '__main__':
    app.run(debug=os.environ.get('FLASK_DEBUG', '0').lower() in ('1', 'true'), port=20000, host="0.0.0.0")
