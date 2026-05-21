# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 数据库模型
"""
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db
import uuid


# 用户模型
class User(UserMixin, db.Model):
    """用户表"""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, index=True)
    phone = db.Column(db.String(20), unique=True, index=True)
    email = db.Column(db.String(120), unique=True, nullable=True)
    password_hash = db.Column(db.String(256))
    
    # 用户类型
    role = db.Column(db.String(20), default='citizen')  # citizen, volunteer, security, grid_worker, cloud_sentinel, admin, police
    
    # 实名认证信息
    real_name = db.Column(db.String(64), nullable=True)
    id_card = db.Column(db.String(18), nullable=True)  # 身份证号（加密存储）
    is_verified = db.Column(db.Boolean, default=False)  # 是否实名认证
    
    # 头像
    avatar = db.Column(db.String(256), default='default_avatar.png')
    
    # 积分系统
    points = db.Column(db.Integer, default=0)
    total_points = db.Column(db.Integer, default=0)  # 累计积分
    
    # 状态
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime, nullable=True)
    
    # 关联
    clues = db.relationship('Clue', foreign_keys='Clue.reporter_id', backref='reporter', lazy='dynamic')
    tasks = db.relationship('TaskAssignment', foreign_keys='TaskAssignment.user_id', backref='assignee', lazy='dynamic')
    rewards = db.relationship('RewardClaim', backref='claimer', lazy='dynamic')
    # 安保人员/网格员额外信息
    work_unit = db.Column(db.String(128), nullable=True)  # 工作单位
    work_address = db.Column(db.String(256), nullable=True)  # 工作地址
    emergency_contact = db.Column(db.String(20), nullable=True)  # 紧急联系人
    lat = db.Column(db.Float, nullable=True)  # 纬度
    lng = db.Column(db.Float, nullable=True)  # 经度
    is_on_duty = db.Column(db.Boolean, default=False)  # 是否值班
    last_checkin = db.Column(db.DateTime, nullable=True)  # 最后打卡时间
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def add_points(self, points, reason=''):
        """增加积分"""
        self.points += points
        self.total_points += points
        # 记录积分变动
        point_log = PointLog(user_id=self.id, points=points, reason=reason)
        db.session.add(point_log)
        db.session.commit()
    
    def __repr__(self):
        return f'<User {self.username}>'


# 积分记录
class PointLog(db.Model):
    """积分变动记录"""
    __tablename__ = 'point_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    points = db.Column(db.Integer)  # 正数为增加，负数为减少
    reason = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', backref='point_logs')


# 悬赏令
class Reward(db.Model):
    """悬赏令表"""
    __tablename__ = 'rewards'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    content = db.Column(db.Text)
    
    # 案件类型
    case_type = db.Column(db.String(50))  # 刑事案件、治安案件、寻人启事、失物招领等
    
    # 悬赏金额
    reward_amount = db.Column(db.Float, default=0)
    reward_type = db.Column(db.String(20), default='cash')  # cash, points
    
    # 嫌疑人/目标信息
    suspect_name = db.Column(db.String(64), nullable=True)
    suspect_description = db.Column(db.Text, nullable=True)
    suspect_photo = db.Column(db.String(256), nullable=True)
    
    # 案发地点
    location = db.Column(db.String(256), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    
    # 状态
    status = db.Column(db.String(20), default='active')  # active, pending, completed, cancelled
    
    # 发布信息
    published_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    deadline = db.Column(db.DateTime, nullable=True)  # 截止日期
    
    # 浏览量
    view_count = db.Column(db.Integer, default=0)
    
    # 关联
    clues = db.relationship('Clue', backref='reward', lazy='dynamic')
    
    publisher = db.relationship('User', foreign_keys=[published_by])
    
    def __repr__(self):
        return f'<Reward {self.title}>'


# 线索举报
class Clue(db.Model):
    """线索举报表"""
    __tablename__ = 'clues'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 线索编号（对外展示）
    clue_no = db.Column(db.String(32), unique=True, index=True)
    
    # 关联悬赏令（可为空，普通举报）
    reward_id = db.Column(db.Integer, db.ForeignKey('rewards.id'), nullable=True)
    
    # 举报人
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # 匿名举报
    is_anonymous = db.Column(db.Boolean, default=False)
    anonymous_code = db.Column(db.String(32), nullable=True)  # 匿名查询码
    
    # 举报内容
    content = db.Column(db.Text)
    
    # 线索类型（AI识别或用户选择）
    clue_type = db.Column(db.String(50), nullable=True)  # 消防隐患、治安问题、刑事案件等
    
    # 位置信息
    location = db.Column(db.String(256), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    address_from_gps = db.Column(db.String(256), nullable=True)  # GPS解析的地址
    
    # 媒体文件（JSON数组存储多个文件路径）
    media_files = db.Column(db.Text, default='[]')
    
    # 联系方式（匿名举报时可选）
    contact_phone = db.Column(db.String(20), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)
    
    # 状态流转
    status = db.Column(db.String(20), default='submitted')
    # submitted -> reviewing -> investigating -> verified -> closed/rewarded
    
    # 处理信息
    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)  # 指派给哪位民警
    handler_notes = db.Column(db.Text, nullable=True)  # 处理备注
    handler_photos = db.Column(db.Text, default='[]')  # 处理过程照片
    
    # 时间戳
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # 奖励信息
    reward_given = db.Column(db.Float, default=0)
    reward_points = db.Column(db.Integer, default=0)
    
    # 反馈评价
    rating = db.Column(db.Integer, nullable=True)  # 1-5星评价
    feedback = db.Column(db.Text, nullable=True)
    
    handler = db.relationship('User', foreign_keys=[assigned_to])
    
    def __init__(self, **kwargs):
        super(Clue, self).__init__(**kwargs)
        if not self.clue_no:
            self.clue_no = f"XS{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:6].upper()}"
        if not self.anonymous_code:
            self.anonymous_code = str(uuid.uuid4())[:12].upper()
    
    def __repr__(self):
        return f'<Clue {self.clue_no}>'


# 安全隐患
class Hazard(db.Model):
    """安全隐患表"""
    __tablename__ = 'hazards'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 隐患编号
    hazard_no = db.Column(db.String(32), unique=True, index=True)
    
    # 上报人
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    
    # 隐患类型
    hazard_type = db.Column(db.String(50))  # 消防通道堵塞、井盖缺失、路灯损坏等
    
    # 描述
    description = db.Column(db.Text)
    
    # 位置
    location = db.Column(db.String(256))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    
    # 照片
    photos = db.Column(db.Text, default='[]')
    
    # 状态
    status = db.Column(db.String(20), default='pending')  # pending, processing, resolved, ignored
    
    # 处理信息
    handler_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    handle_notes = db.Column(db.Text, nullable=True)
    handle_photos = db.Column(db.Text, default='[]')
    
    # 时间戳
    reported_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # 紧急程度
    urgency = db.Column(db.String(20), default='normal')  # low, normal, high, urgent
    
    reporter = db.relationship('User', foreign_keys=[reporter_id])
    handler = db.relationship('User', foreign_keys=[handler_id])
    
    def __init__(self, **kwargs):
        super(Hazard, self).__init__(**kwargs)
        if not self.hazard_no:
            self.hazard_no = f"YH{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:6].upper()}"
    
    def __repr__(self):
        return f'<Hazard {self.hazard_no}>'


# 任务系统
class Task(db.Model):
    """任务表"""
    __tablename__ = 'tasks'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 任务编号
    task_no = db.Column(db.String(32), unique=True, index=True)
    
    # 任务标题和描述
    title = db.Column(db.String(128))
    description = db.Column(db.Text)
    
    # 任务类型
    task_type = db.Column(db.String(50))  # patrol:巡逻, propaganda:宣传, emergency:应急, investigation:调查
    
    # 任务地点
    location = db.Column(db.String(256))
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    
    # 任务范围（米）
    radius = db.Column(db.Integer, default=500)
    
    # 奖励
    reward_points = db.Column(db.Integer, default=0)
    reward_cash = db.Column(db.Float, default=0)
    
    # 时间
    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)
    
    # 需要人数
    required_people = db.Column(db.Integer, default=1)
    
    # 状态
    status = db.Column(db.String(20), default='open')  # open, assigned, in_progress, completed, cancelled
    
    # 发布人
    published_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 关联
    assignments = db.relationship('TaskAssignment', backref='task', lazy='dynamic')
    
    publisher = db.relationship('User', foreign_keys=[published_by])
    
    def __init__(self, **kwargs):
        super(Task, self).__init__(**kwargs)
        if not self.task_no:
            self.task_no = f"RW{datetime.now().strftime('%Y%m%d%H%M%S')}{str(uuid.uuid4())[:6].upper()}"
    
    def __repr__(self):
        return f'<Task {self.title}>'


# 任务分配
class TaskAssignment(db.Model):
    """任务分配表"""
    __tablename__ = 'task_assignments'
    
    id = db.Column(db.Integer, primary_key=True)
    
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'))
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 状态
    status = db.Column(db.String(20), default='assigned')  # assigned, in_progress, completed, cancelled
    
    # 接单时间
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 开始时间
    started_at = db.Column(db.DateTime, nullable=True)
    
    # 完成时间
    completed_at = db.Column(db.DateTime, nullable=True)
    
    # 完成证明（照片）
    proof_photos = db.Column(db.Text, default='[]')
    
    # 完成备注
    completion_notes = db.Column(db.Text, nullable=True)
    
    # 审核状态
    is_verified = db.Column(db.Boolean, default=False)
    verified_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    verified_at = db.Column(db.DateTime, nullable=True)
    
    def __repr__(self):
        return f'<TaskAssignment {self.id}>'


# 巡逻打卡
class PatrolCheckin(db.Model):
    """巡逻打卡记录"""
    __tablename__ = 'patrol_checkins'
    
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    
    # 打卡位置
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    location = db.Column(db.String(256))
    
    # 打卡照片
    photo = db.Column(db.String(256), nullable=True)
    
    # 备注
    notes = db.Column(db.Text, nullable=True)
    
    # 打卡时间
    checkin_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 是否异常
    is_abnormal = db.Column(db.Boolean, default=False)
    abnormal_reason = db.Column(db.String(256), nullable=True)
    
    user = db.relationship('User', backref='patrol_checkins')
    
    def __repr__(self):
        return f'<PatrolCheckin {self.id}>'


# 应急调度
class EmergencyDispatch(db.Model):
    """应急调度记录"""
    __tablename__ = 'emergency_dispatches'
    
    id = db.Column(db.Integer, primary_key=True)
    
    # 事件标题
    title = db.Column(db.String(128))
    
    # 事件描述
    description = db.Column(db.Text)
    
    # 事件位置
    location = db.Column(db.String(256))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    
    # 事件类型
    emergency_type = db.Column(db.String(50))  # 突发事件、群体性事件、自然灾害等
    
    # 紧急程度
    urgency = db.Column(db.String(20), default='high')  # low, normal, high, urgent
    
    # 调度范围（米）
    dispatch_radius = db.Column(db.Integer, default=1000)
    
    # 状态
    status = db.Column(db.String(20), default='dispatching')  # dispatching, responding, resolved, cancelled
    
    # 调度人
    dispatched_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    dispatched_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 响应人员（JSON数组）
    responders = db.Column(db.Text, default='[]')
    
    # 解决时间
    resolved_at = db.Column(db.DateTime, nullable=True)
    
    # 解决备注
    resolution_notes = db.Column(db.Text, nullable=True)
    
    dispatcher = db.relationship('User', foreign_keys=[dispatched_by])
    
    def __repr__(self):
        return f'<EmergencyDispatch {self.title}>'


# 公告/新闻
class Announcement(db.Model):
    """公告表"""
    __tablename__ = 'announcements'
    
    id = db.Column(db.Integer, primary_key=True)
    
    title = db.Column(db.String(128))
    content = db.Column(db.Text)
    
    # 类型
    category = db.Column(db.String(50), default='notice')  # notice:通知, news:新闻, safety:安全提示
    
    # 是否置顶
    is_pinned = db.Column(db.Boolean, default=False)
    
    # 浏览量
    view_count = db.Column(db.Integer, default=0)
    
    # 发布人
    published_by = db.Column(db.Integer, db.ForeignKey('users.id'))
    published_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # 封面图
    cover_image = db.Column(db.String(256), nullable=True)
    
    publisher = db.relationship('User', foreign_keys=[published_by])
    
    def __repr__(self):
        return f'<Announcement {self.title}>'


# 兑换商品
class RewardItem(db.Model):
    """积分兑换商品"""
    __tablename__ = 'reward_items'
    
    id = db.Column(db.Integer, primary_key=True)
    
    name = db.Column(db.String(128))
    description = db.Column(db.Text, nullable=True)
    
    # 所需积分
    required_points = db.Column(db.Integer)
    
    # 库存
    stock = db.Column(db.Integer, default=0)
    
    # 商品图片
    image = db.Column(db.String(256), nullable=True)
    
    # 是否上架
    is_active = db.Column(db.Boolean, default=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<RewardItem {self.name}>'


# 兑换记录
class RewardClaim(db.Model):
    """积分兑换记录"""
    __tablename__ = 'reward_claims'
    
    id = db.Column(db.Integer, primary_key=True)
    
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    item_id = db.Column(db.Integer, db.ForeignKey('reward_items.id'))
    
    # 兑换数量
    quantity = db.Column(db.Integer, default=1)
    
    # 消耗积分
    points_spent = db.Column(db.Integer)
    
    # 状态
    status = db.Column(db.String(20), default='pending')  # pending, shipped, completed, cancelled
    
    # 收货信息
    receiver_name = db.Column(db.String(64), nullable=True)
    receiver_phone = db.Column(db.String(20), nullable=True)
    receiver_address = db.Column(db.String(256), nullable=True)
    
    # 物流信息
    tracking_no = db.Column(db.String(64), nullable=True)
    
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    shipped_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)
    
    item = db.relationship('RewardItem')
    
    def __repr__(self):
        return f'<RewardClaim {self.id}>'


# 系统配置
class SystemConfig(db.Model):
    """系统配置表"""
    __tablename__ = 'system_configs'
    
    id = db.Column(db.Integer, primary_key=True)
    
    key = db.Column(db.String(64), unique=True, index=True)
    value = db.Column(db.Text)
    description = db.Column(db.String(256), nullable=True)
    
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<SystemConfig {self.key}>'
