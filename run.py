#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 启动脚本
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models import User, SystemConfig
from flask_migrate import upgrade

# 创建应用实例
app = create_app(os.getenv('FLASK_CONFIG', 'development'))


@app.cli.command()
def deploy():
    """部署命令"""
    # 执行数据库迁移
    upgrade()
    
    # 创建默认管理员账号
    create_admin()
    
    print('部署完成！')


def create_admin():
    """创建默认管理员账号 - 优先使用.env配置"""
    import os
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'admin123')
    admin_phone = os.environ.get('ADMIN_PHONE', '13800138000')

    admin = User.query.filter_by(username=admin_username).first()
    if not admin:
        admin = User(
            username=admin_username,
            phone=admin_phone,
            email='admin@police.gov.cn',
            role='admin',
            is_verified=True,
            is_active=True
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()
        print(f'管理员账号已创建：{admin_username} / {admin_password}')
    else:
        print(f'管理员账号已存在：{admin_username}')


@app.shell_context_processor
def make_shell_context():
    """Shell上下文"""
    return {
        'db': db,
        'User': User,
        'SystemConfig': SystemConfig
    }


if __name__ == '__main__':
    # 开发环境运行
    app.run(host='0.0.0.0', port=5000, debug=True)
