from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager

# 统一的扩展对象入口

db = SQLAlchemy()
login_manager = LoginManager()
