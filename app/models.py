# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 数据库模型
"""
import os
from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from cryptography.fernet import Fernet
from app import db
import uuid

# ID card encryption setup
_ENCRYPTION_KEY = os.environ.get('ENCRYPTION_KEY')
if _ENCRYPTION_KEY:
    _fernet = Fernet(_ENCRYPTION_KEY.encode() if isinstance(_ENCRYPTION_KEY, str) else _ENCRYPTION_KEY)
else:
    _fernet = None


def encrypt_id_card(plaintext):
    """加密身份证号"""
    if not plaintext or not _fernet:
        return plaintext
    return _fernet.encrypt(plaintext.encode()).decode()


def decrypt_id_card(ciphertext):
    """解密身份证号"""
    if not ciphertext or not _fernet:
        return ciphertext
    try:
        return _fernet.decrypt(ciphertext.encode()).decode()
    except Exception:
        return ciphertext


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
    role = db.Column(db.String(20), default='citizen', index=True)

    # 实名认证信息（身份证号加密存储）
    real_name = db.Column(db.String(64), nullable=True)
    _id_card_encrypted = db.Column('id_card', db.String(256), nullable=True)
    is_verified = db.Column(db.Boolean, default=False)

    # 头像
    avatar = db.Column(db.String(256), default='default_avatar.png')

    # 积分系统
    points = db.Column(db.Integer, default=0)
    total_points = db.Column(db.Integer, default=0)

    # 状态
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    last_login = db.Column(db.DateTime, nullable=True)

    # 关联
    clues = db.relationship('Clue', foreign_keys='Clue.reporter_id', backref='reporter', lazy='dynamic')
    tasks = db.relationship('TaskAssignment', foreign_keys='TaskAssignment.user_id', backref='assignee', lazy='dynamic')
    rewards = db.relationship('RewardClaim', backref='claimer', lazy='dynamic')

    # 安保人员/网格员额外信息
    work_unit = db.Column(db.String(128), nullable=True)
    work_address = db.Column(db.String(256), nullable=True)
    emergency_contact = db.Column(db.String(20), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    is_on_duty = db.Column(db.Boolean, default=False)
    last_checkin = db.Column(db.DateTime, nullable=True)

    @property
    def id_card(self):
        return decrypt_id_card(self._id_card_encrypted)

    @id_card.setter
    def id_card(self, value):
        self._id_card_encrypted = encrypt_id_card(value)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def add_points(self, points, reason=''):
        """增加积分"""
        self.points += points
        self.total_points += points
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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    points = db.Column(db.Integer)
    reason = db.Column(db.String(256))
    created_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

    user = db.relationship('User', backref='point_logs')


# 悬赏令
class Reward(db.Model):
    """悬赏令表"""
    __tablename__ = 'rewards'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(128))
    content = db.Column(db.Text)

    case_type = db.Column(db.String(50), index=True)
    reward_amount = db.Column(db.Float, default=0)
    reward_type = db.Column(db.String(20), default='cash')

    suspect_name = db.Column(db.String(64), nullable=True)
    suspect_description = db.Column(db.Text, nullable=True)
    suspect_photo = db.Column(db.String(256), nullable=True)

    location = db.Column(db.String(256), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)

    status = db.Column(db.String(20), default='active', index=True)

    published_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    deadline = db.Column(db.DateTime, nullable=True)

    view_count = db.Column(db.Integer, default=0)

    clues = db.relationship('Clue', backref='reward', lazy='dynamic')
    publisher = db.relationship('User', foreign_keys=[published_by])

    def __repr__(self):
        return f'<Reward {self.title}>'


# 线索举报
class Clue(db.Model):
    """线索举报表"""
    __tablename__ = 'clues'

    id = db.Column(db.Integer, primary_key=True)
    clue_no = db.Column(db.String(32), unique=True, index=True)

    reward_id = db.Column(db.Integer, db.ForeignKey('rewards.id'), nullable=True, index=True)
    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    is_anonymous = db.Column(db.Boolean, default=False)
    anonymous_code = db.Column(db.String(32), nullable=True)

    content = db.Column(db.Text)

    clue_type = db.Column(db.String(50), nullable=True)

    location = db.Column(db.String(256), nullable=True)
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    address_from_gps = db.Column(db.String(256), nullable=True)

    media_files = db.Column(db.Text, default='[]')

    contact_phone = db.Column(db.String(20), nullable=True)
    contact_email = db.Column(db.String(120), nullable=True)

    status = db.Column(db.String(20), default='submitted', index=True)

    assigned_to = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    handler_notes = db.Column(db.Text, nullable=True)
    handler_photos = db.Column(db.Text, default='[]')

    submitted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    reviewed_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    reward_given = db.Column(db.Float, default=0)
    reward_points = db.Column(db.Integer, default=0)

    rating = db.Column(db.Integer, nullable=True)
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
    hazard_no = db.Column(db.String(32), unique=True, index=True)

    reporter_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)

    hazard_type = db.Column(db.String(50), index=True)
    description = db.Column(db.Text)

    location = db.Column(db.String(256))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

    photos = db.Column(db.Text, default='[]')

    status = db.Column(db.String(20), default='pending', index=True)

    handler_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    handle_notes = db.Column(db.Text, nullable=True)
    handle_photos = db.Column(db.Text, default='[]')

    reported_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    resolved_at = db.Column(db.DateTime, nullable=True)

    urgency = db.Column(db.String(20), default='normal', index=True)

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
    task_no = db.Column(db.String(32), unique=True, index=True)

    title = db.Column(db.String(128))
    description = db.Column(db.Text)

    task_type = db.Column(db.String(50), index=True)

    location = db.Column(db.String(256))
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)

    radius = db.Column(db.Integer, default=500)

    reward_points = db.Column(db.Integer, default=0)
    reward_cash = db.Column(db.Float, default=0)

    start_time = db.Column(db.DateTime)
    end_time = db.Column(db.DateTime)

    required_people = db.Column(db.Integer, default=1)

    status = db.Column(db.String(20), default='open', index=True)

    published_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

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
    task_id = db.Column(db.Integer, db.ForeignKey('tasks.id'), index=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)

    status = db.Column(db.String(20), default='assigned', index=True)
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)
    started_at = db.Column(db.DateTime, nullable=True)
    completed_at = db.Column(db.DateTime, nullable=True)

    proof_photos = db.Column(db.Text, default='[]')
    completion_notes = db.Column(db.Text, nullable=True)

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
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)

    lat = db.Column(db.Float)
    lng = db.Column(db.Float)
    location = db.Column(db.String(256))

    photo = db.Column(db.String(256), nullable=True)
    notes = db.Column(db.Text, nullable=True)

    checkin_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

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
    title = db.Column(db.String(128))
    description = db.Column(db.Text)

    location = db.Column(db.String(256))
    lat = db.Column(db.Float)
    lng = db.Column(db.Float)

    emergency_type = db.Column(db.String(50))
    urgency = db.Column(db.String(20), default='high')

    dispatch_radius = db.Column(db.Integer, default=1000)

    status = db.Column(db.String(20), default='dispatching', index=True)

    dispatched_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    dispatched_at = db.Column(db.DateTime, default=datetime.utcnow)

    responders = db.Column(db.Text, default='[]')

    resolved_at = db.Column(db.DateTime, nullable=True)
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

    category = db.Column(db.String(50), default='notice', index=True)
    is_pinned = db.Column(db.Boolean, default=False)
    view_count = db.Column(db.Integer, default=0)

    published_by = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    published_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)

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

    required_points = db.Column(db.Integer)
    stock = db.Column(db.Integer, default=0)

    image = db.Column(db.String(256), nullable=True)

    is_active = db.Column(db.Boolean, default=True, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<RewardItem {self.name}>'


# 兑换记录
class RewardClaim(db.Model):
    """积分兑换记录"""
    __tablename__ = 'reward_claims'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), index=True)
    item_id = db.Column(db.Integer, db.ForeignKey('reward_items.id'), index=True)

    quantity = db.Column(db.Integer, default=1)
    points_spent = db.Column(db.Integer)

    status = db.Column(db.String(20), default='pending', index=True)

    receiver_name = db.Column(db.String(64), nullable=True)
    receiver_phone = db.Column(db.String(20), nullable=True)
    receiver_address = db.Column(db.String(256), nullable=True)

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
