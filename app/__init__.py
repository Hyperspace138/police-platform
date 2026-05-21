# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 应用工厂
"""
import os
from dotenv import load_dotenv
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)

from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_migrate import Migrate
from flask_moment import Moment
from config.config import config

# 初始化扩展
db = SQLAlchemy()
login_manager = LoginManager()
migrate = Migrate()
moment = Moment()


def create_app(config_name='default'):
    """
    应用工厂函数
    :param config_name: 配置名称
    :return: Flask应用实例
    """
    app = Flask(__name__)
    
    # 加载配置
    app.config.from_object(config[config_name])
    app.config['AMAP_KEY'] = os.environ.get('AMAP_KEY', app.config['AMAP_KEY'])
    print("AMAP_KEY from config:", app.config.get('AMAP_KEY'))
    # 确保上传目录存在
    
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # 初始化扩展
    db.init_app(app)
    login_manager.init_app(app)
    migrate.init_app(app, db)
    moment.init_app(app)
    
    # 配置登录管理
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
    
    # 注册模板过滤器
    from app.utils.filters import register_filters
    register_filters(app)
    
    # 创建数据库表
    with app.app_context():
        db.create_all()
    
    return app
