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
    
    # 密钥配置（生产环境请修改为随机字符串）
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'your-secret-key-here-change-in-production'
    
    # 数据库配置
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(BASE_DIR, 'app.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_COMMIT_ON_TEARDOWN = True
    
    # 文件上传配置
    UPLOAD_FOLDER = os.path.join(BASE_DIR, 'app', 'static', 'uploads')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 最大16MB
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov'}
    
    # 会话配置
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    
    # 分页配置
    POSTS_PER_PAGE = 10
    
    # 高德地图API Key（需要自行申请）
    AMAP_KEY = os.environ.get('AMAP_KEY') or 'your-amap-key-here'
    
    # 高德地图安全密钥
    AMAP_SECURITY_CODE = os.environ.get('AMAP_SECURITY_CODE') or 'your-security-code-here'
    # 积分配置
    POINTS_CONFIG = {
        'clue_submit': 10,          # 提交线索基础积分
        'clue_adopted': 50,         # 线索被采纳积分
        'task_complete': 30,        # 完成任务积分
        'patrol_checkin': 5,        # 巡逻打卡积分
        'emergency_response': 100,  # 应急响应积分
    }
    
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


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    

class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    
    # 生产环境使用MySQL
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'mysql+pymysql://username:password@localhost/police_platform'


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
