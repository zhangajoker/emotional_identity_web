import os

import pymysql
from pymysql.cursors import DictCursor


def get_db_config():
    db_user = os.environ.get("DB_USER")
    db_password = os.environ.get("DB_PASSWORD")

    if not db_user or not db_password:
        raise RuntimeError(
            "缺少 DB_USER 或 DB_PASSWORD，请检查 .env 配置"
        )

    return {
        'host': os.environ.get('DB_HOST', 'db'),
        'user': db_user,
        'password': db_password,
        'database': os.environ.get('DB_NAME', 'emotion_db'),
        'charset': 'utf8mb4',
        'use_unicode': True,
        'cursorclass': DictCursor,
        'autocommit': True,
    }


def get_connection():
    return pymysql.connect(**get_db_config())