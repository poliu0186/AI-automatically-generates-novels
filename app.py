from app import create_app

app = create_app()

if __name__ == '__main__':
    import os
    app.run(
        debug=os.environ.get('FLASK_DEBUG', '0').strip().lower() in ('1', 'true', 'yes'),
        port=int(os.environ.get('PORT', '60001')),
        host=os.environ.get('HOST', '0.0.0.0'),
    )
