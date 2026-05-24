# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 配置文件
"""
import os
from datetime import timedelta

# 获取项目根目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Config:
    """基础配置类"""

    # 密钥配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'

    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大16MB

    # 会话安全配置
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_COOKIE_SECURE = False  # 生产环境通过Nginx HTTPS配置
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'

    # CSRF保护
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1小时

    # 分页配置
    POSTS_PER_PAGE = 10

    # 高德地图API Key
    AMAP_KEY = os.environ.get('AMAP_KEY') or 'your-amap-key-here'
    AMAP_SECURITY_CODE = os.environ.get('AMAP_SECURITY_CODE', '')

    # 积分配置
    POINTS_CONFIG = {
        'clue_submit': 10,
        'clue_adopted': 50,
        'task_complete': 30,
        'patrol_checkin': 5,
        'emergency_response': 100,
        'register': 20,
        'malicious_penalty': -20,  # 恶意举报扣分
    }

    # 防刷分机制
    PATROL_MIN_INTERVAL = 300  # 巡逻打卡最小间隔（秒），5分钟
    PATROL_MIN_DISTANCE = 100  # 巡逻打卡最小距离（米），100米内视为重复
    TASK_CLAIM_DAILY_LIMIT = 10  # 每日抢单上限
    HAZARD_DUPLICATE_RADIUS = 50  # 隐患去重半径（米）
    HAZARD_DUPLICATE_HOURS = 24  # 隐患去重时间窗口（小时）

    # 悬赏令状态
    REWARD_STATUS = {
        'active': '进行中',
        'pending': '待审核',
        'completed': '已结案',
        'cancelled': '已取消'
    }

    # 线索状态
    CLUE_STATUS = {
        'submitted': '已提交',
        'reviewing': '审核中',
        'investigating': '核查中',
        'verified': '已核实',
        'closed': '已办结',
        'rewarded': '已奖励'
    }

    # 任务状态
    TASK_STATUS = {
        'open': '可抢单',
        'assigned': '已接单',
        'in_progress': '进行中',
        'completed': '已完成',
        'cancelled': '已取消'
    }

    # 用户角色
    USER_ROLES = {
        'citizen': '普通群众',
        'volunteer': '志愿者',
        'security': '安保人员',
        'grid_worker': '网格员',
        'cloud_sentinel': '云哨兵',
        'admin': '管理员',
        'police': '民警'
    }

    # 缓存配置
    CACHE_TYPE = 'SimpleCache'
    CACHE_DEFAULT_TIMEOUT = 60


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    WTF_CSRF_ENABLED = True


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://username:password@localhost/police_platform'
    SESSION_COOKIE_SECURE = True


class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    WTF_CSRF_ENABLED = False


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}
