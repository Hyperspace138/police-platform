# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 应用工厂
"""
import os
import logging
from logging.handlers import RotatingFileHandler
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

from flask import Flask, render_template
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_moment import Moment
from flask_wtf.csrf import CSRFProtect
from flask_talisman import Talisman
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_caching import Cache
from config.config import config

# 初始化扩展
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
moment = Moment()
csrf = CSRFProtect()
cache = Cache()
limiter = Limiter(key_func=get_remote_address, default_limits=['200 per day', '60 per hour'])


def setup_logging(app):
    """配置应用日志"""
    if not app.debug:
        log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
        os.makedirs(log_dir, exist_ok=True)

        file_handler = RotatingFileHandler(
            os.path.join(log_dir, 'police_platform.log'),
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s [%(name)s] %(message)s'
        ))
        file_handler.setLevel(logging.INFO)
        app.logger.addHandler(file_handler)

        # 安全审计日志
        audit_handler = RotatingFileHandler(
            os.path.join(log_dir, 'audit.log'),
            maxBytes=10 * 1024 * 1024,
            backupCount=5
        )
        audit_handler.setFormatter(logging.Formatter(
            '%(asctime)s %(levelname)s %(message)s'
        ))
        audit_logger = logging.getLogger('audit')
        audit_logger.addHandler(audit_handler)
        audit_logger.setLevel(logging.INFO)

    app.logger.setLevel(logging.INFO)
    app.logger.info('Police Platform starting')


def create_app(config_name='default'):
    """应用工厂函数"""
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    app.config['AMAP_KEY'] = os.environ.get('AMAP_KEY', app.config['AMAP_KEY'])

    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    moment.init_app(app)
    csrf.init_app(app)
    cache.init_app(app)
    limiter.init_app(app)

    # 配置安全响应头 (Talisman)
    csp = {
        'default-src': ["'self'"],
        'script-src': ["'self'", "'unsafe-inline'", "'unsafe-eval'",
                       'https://cdn.jsdelivr.net', 'https://webapi.amap.com',
                       'https://restapi.amap.com', 'https://vdata.amap.com'],
        'style-src': ["'self'", "'unsafe-inline'", 'https://cdn.jsdelivr.net',
                      'https://webapi.amap.com'],
        'img-src': ["'self'", 'data:', 'blob:',
                    'https://webapi.amap.com', 'https://vdata.amap.com',
                    'https://images.unsplash.com'],
        'connect-src': ["'self'", 'wss:', 'https://restapi.amap.com',
                        'https://webapi.amap.com', 'https://vdata.amap.com'],
        'font-src': ["'self'", 'https://cdn.jsdelivr.net'],
        'worker-src': ["'self'", 'blob:'],
        'child-src': ["'self'", 'blob:'],
    }
    Talisman(app, content_security_policy=csp, force_https=False,
             session_cookie_secure=False)

    # 登录管理配置
    login_manager.login_view = 'auth.login'
    login_manager.login_message = '请先登录以访问此页面'
    login_manager.login_message_category = 'warning'

    @app.context_processor
    def inject_amap_config():
        return dict(
            amap_key=app.config['AMAP_KEY'],
            amap_security_code=app.config.get('AMAP_SECURITY_CODE', '')
        )

    # 注册蓝图
    from app.routes import main, auth, api, admin
    app.register_blueprint(main.bp)
    app.register_blueprint(auth.bp, url_prefix='/auth')
    app.register_blueprint(api.bp, url_prefix='/api')
    app.register_blueprint(admin.bp, url_prefix='/admin')

    # CSRF豁免 — API端点使用header验证，不需CSRF
    csrf.exempt(api.bp)

    # 注册模板过滤器
    from app.utils.filters import register_filters
    register_filters(app)

    # 全局错误处理
    @app.errorhandler(404)
    def not_found_error(error):
        return render_template('errors/404.html'), 404

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        app.logger.error(f'500 error: {error}', exc_info=True)
        return render_template('errors/500.html'), 500

    @app.errorhandler(429)
    def ratelimit_error(error):
        return render_template('errors/429.html'), 429

    @app.errorhandler(413)
    def too_large_error(error):
        from flask import flash, redirect, url_for
        flash('文件大小超过限制（最大16MB）', 'danger')
        return redirect(url_for('main.index'))

    # 创建数据库表
    with app.app_context():
        db.create_all()

    # 设置日志
    setup_logging(app)

    return app
