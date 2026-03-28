import re
from io import BytesIO
from openai import OpenAI
from flask import Blueprint, request, Response, current_app, send_file
from flask_login import login_required

try:
    from docx import Document
    DOCX_AVAILABLE = True
except ImportError:
    DOCX_AVAILABLE = False

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

api_bp = Blueprint('api', __name__)


def get_client(endpoint, api_key):
    return OpenAI(base_url=endpoint, api_key=api_key)


@api_bp.route('/gen', methods=['POST'])
@login_required
def generate():
    data = request.json
    prompt = data.get('prompt', '')
    current_app.logger.debug(f"Received prompt for gen: {prompt}")

    client = get_client(current_app.config['API_ENDPOINT_1'], current_app.config['API_KEY_1'])
    logger = current_app.logger

    def generate_stream():
        try:
            completion = client.chat.completions.create(
                model="glm-4.5-air",
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            logger.debug("Stream created successfully for gen")
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    logger.debug(f"Yielding chunk: {chunk.choices[0].delta.content}")
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error in generate_stream: {e}")
            yield f"Error: {str(e)}"

    return Response(generate_stream(), mimetype='text/plain')


@api_bp.route('/gen2', methods=['POST'])
@login_required
def generate2():
    data = request.json
    prompt = data.get('prompt', '')
    current_app.logger.debug(f"Received prompt for gen2: {prompt}")

    client = get_client(current_app.config['API_ENDPOINT_2'], current_app.config['API_KEY_2'])
    logger = current_app.logger

    def generate_stream():
        try:
            completion = client.chat.completions.create(
                model="glm-4.5-air",
                messages=[{"role": "user", "content": prompt}],
                stream=True
            )
            logger.debug("Stream created successfully for gen2")
            for chunk in completion:
                if chunk.choices[0].delta.content is not None:
                    logger.debug(f"Yielding chunk: {chunk.choices[0].delta.content}")
                    yield chunk.choices[0].delta.content
        except Exception as e:
            logger.error(f"Error in generate_stream: {e}")
            yield f"Error: {str(e)}"

    return Response(generate_stream(), mimetype='text/plain')


@api_bp.route('/download', methods=['POST'])
@login_required
def download_novel():
    data = request.json
    content = data.get('content', '')
    format_type = data.get('format', 'txt')
    title = data.get('title', 'generated_novel')

    if not content:
        return {'error': 'No content provided'}, 400

    content = re.sub(r'<[^>]+>', '', content)

    if format_type == 'txt':
        buffer = BytesIO()
        buffer.write(content.encode('utf-8'))
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{title}.txt",
            mimetype='text/plain'
        )

    elif format_type == 'docx':
        if not DOCX_AVAILABLE:
            return {'error': 'DOCX format not available. Please install python-docx'}, 400

        doc = Document()
        doc.add_heading(title, 0)
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                doc.add_paragraph(para.strip())

        buffer = BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{title}.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    elif format_type == 'pdf':
        if not PDF_AVAILABLE:
            return {'error': 'PDF format not available. Please install reportlab'}, 400

        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        paragraphs = content.split('\n\n')
        for para in paragraphs:
            if para.strip():
                story.append(Paragraph(para.strip(), styles['Normal']))

        doc.build(story)
        buffer.seek(0)
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f"{title}.pdf",
            mimetype='application/pdf'
        )

    else:
        return {'error': 'Unsupported format'}, 400
