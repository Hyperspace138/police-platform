# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 认证路由
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, session
from flask_login import login_user, logout_user, login_required, current_user
from app import db, login_manager
from app.models import User
from datetime import datetime

bp = Blueprint('auth', __name__)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@bp.route('/register', methods=['GET', 'POST'])
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        phone = request.form.get('phone')
        password = request.form.get('password')
        password2 = request.form.get('password2')
        
        # 验证
        if not all([username, phone, password]):
            flash('请填写所有必填项', 'danger')
            return redirect(url_for('auth.register'))
        
        if password != password2:
            flash('两次输入的密码不一致', 'danger')
            return redirect(url_for('auth.register'))
        
        if len(password) < 6:
            flash('密码长度至少为6位', 'danger')
            return redirect(url_for('auth.register'))
        
        # 检查用户名和手机号是否已存在
        if User.query.filter_by(username=username).first():
            flash('用户名已被使用', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(phone=phone).first():
            flash('手机号已被注册', 'danger')
            return redirect(url_for('auth.register'))
        
        # 创建用户
        user = User(username=username, phone=phone)
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = request.form.get('remember') == 'on'
        
        # 支持用户名或手机号登录
        user = User.query.filter(
            (User.username == username) | (User.phone == username)
        ).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('账号已被禁用', 'danger')
                return redirect(url_for('auth.login'))
            
            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()
            
            # 获取跳转地址
            next_page = request.args.get('next')
            if not next_page:
                next_page = url_for('main.index')
            
            flash(f'欢迎回来，{user.username}！', 'success')
            return redirect(next_page)
        else:
            flash('用户名或密码错误', 'danger')
    
    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    """退出登录"""
    logout_user()
    flash('您已退出登录', 'info')
    return redirect(url_for('main.index'))


@bp.route('/profile')
@login_required
def profile():
    """个人中心"""
    from app.models import Clue, TaskAssignment, PointLog
    
    # 获取用户的线索
    clues = Clue.query.filter_by(reporter_id=current_user.id).\
        order_by(Clue.submitted_at.desc()).limit(5).all()
    
    # 获取用户的任务
    tasks = TaskAssignment.query.filter_by(user_id=current_user.id).\
        order_by(TaskAssignment.assigned_at.desc()).limit(5).all()
    
    # 获取积分记录
    point_logs = PointLog.query.filter_by(user_id=current_user.id).\
        order_by(PointLog.created_at.desc()).limit(10).all()
    
    return render_template('auth/profile.html',
                         clues=clues,
                         tasks=tasks,
                         point_logs=point_logs)


@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """编辑个人资料"""
    if request.method == 'POST':
        real_name = request.form.get('real_name')
        email = request.form.get('email')
        
        current_user.real_name = real_name
        current_user.email = email
        
        db.session.commit()
        flash('资料更新成功', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/edit_profile.html')


@bp.route('/password/change', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    new_password2 = request.form.get('new_password2')
    
    if not current_user.check_password(old_password):
        flash('原密码错误', 'danger')
        return redirect(url_for('auth.profile'))
    
    if new_password != new_password2:
        flash('两次输入的新密码不一致', 'danger')
        return redirect(url_for('auth.profile'))
    
    if len(new_password) < 6:
        flash('新密码长度至少为6位', 'danger')
        return redirect(url_for('auth.profile'))
    
    current_user.set_password(new_password)
    db.session.commit()
    
    flash('密码修改成功', 'success')
    return redirect(url_for('auth.profile'))


@bp.route('/verify', methods=['GET', 'POST'])
@login_required
def verify_identity():
    """实名认证"""
    if current_user.is_verified:
        flash('您已完成实名认证', 'info')
        return redirect(url_for('auth.profile'))
    
    if request.method == 'POST':
        real_name = request.form.get('real_name')
        id_card = request.form.get('id_card')
        
        # 简单的身份证验证（实际应调用公安接口验证）
        if len(id_card) != 18:
            flash('请输入正确的身份证号码', 'danger')
            return redirect(url_for('auth.verify_identity'))
        
        current_user.real_name = real_name
        current_user.id_card = id_card  # 实际应加密存储
        current_user.is_verified = True
        
        db.session.commit()
        
        flash('实名认证成功！', 'success')
        return redirect(url_for('auth.profile'))
    
    return render_template('auth/verify.html')
