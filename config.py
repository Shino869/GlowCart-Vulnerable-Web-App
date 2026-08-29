import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_FOLDER = BASE_DIR / 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Keep credentials out of source control.
# Set DATABASE_URL in your local environment for MySQL.
DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'mysql+pymysql://root@localhost:3306/glowcart?charset=utf8mb4'
)
SQLALCHEMY_DATABASE_URI = os.getenv('SQLALCHEMY_DATABASE_URI', DATABASE_URL)
SQLALCHEMY_TRACK_MODIFICATIONS = False

# Set a strong random SECRET_KEY locally.
SECRET_KEY = os.getenv('SECRET_KEY', 'change-me-in-local-environment')
DEBUG = os.getenv('FLASK_DEBUG', '1') == '1'
UPLOADS_DIR = str(UPLOAD_FOLDER)
