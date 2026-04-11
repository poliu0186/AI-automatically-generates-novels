from app import create_app

app = create_app()

if __name__ == '__main__':
    import os
    app.run(debug=os.environ.get('FLASK_DEBUG', '0') == '1', port=60001, host='0.0.0.0')
