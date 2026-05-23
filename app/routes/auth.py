# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 认证路由
"""
import re
import logging
from flask import Blueprint, render_template, redirect, url_for, request, flash
from flask_login import login_user, logout_user, login_required, current_user
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from app import db, login_manager, limiter
from app.models import User
from app.utils.validators import validate_phone, validate_username, validate_password, validate_email, validate_id_card
from datetime import datetime

bp = Blueprint('auth', __name__)
audit_logger = logging.getLogger('audit')


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


@bp.route('/register', methods=['GET', 'POST'])
@limiter.limit('5 per hour', key_func=get_remote_address)
def register():
    """用户注册"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        phone = request.form.get('phone', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        password2 = request.form.get('password2', '')

        # 验证用户名
        valid, msg = validate_username(username)
        if not valid:
            flash(msg, 'danger')
            return redirect(url_for('auth.register'))

        # 验证手机号
        valid, msg = validate_phone(phone)
        if not valid:
            flash(msg, 'danger')
            return redirect(url_for('auth.register'))

        # 验证邮箱（如有）
        valid, msg = validate_email(email)
        if not valid:
            flash(msg, 'danger')
            return redirect(url_for('auth.register'))

        # 验证密码
        valid, msg = validate_password(password)
        if not valid:
            flash(msg, 'danger')
            return redirect(url_for('auth.register'))

        if password != password2:
            flash('两次输入的密码不一致', 'danger')
            return redirect(url_for('auth.register'))

        # 检查唯一性
        if User.query.filter_by(username=username).first():
            flash('用户名已被使用', 'danger')
            return redirect(url_for('auth.register'))

        if User.query.filter_by(phone=phone).first():
            flash('手机号已被注册', 'danger')
            return redirect(url_for('auth.register'))

        user = User(username=username, phone=phone, email=email if email else None)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()

        audit_logger.info(f'New user registered: {username} ({phone})')
        flash('注册成功！请登录', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@bp.route('/login', methods=['GET', 'POST'])
@limiter.limit('10 per minute', key_func=get_remote_address)
def login():
    """用户登录"""
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        remember = request.form.get('remember') == 'on'

        if not username or not password:
            flash('请输入用户名和密码', 'danger')
            return redirect(url_for('auth.login'))

        user = User.query.filter(
            (User.username == username) | (User.phone == username)
        ).first()

        if user and user.check_password(password):
            if not user.is_active:
                audit_logger.warning(f'Login attempt on disabled account: {username}')
                flash('账号已被禁用', 'danger')
                return redirect(url_for('auth.login'))

            login_user(user, remember=remember)
            user.last_login = datetime.utcnow()
            db.session.commit()

            audit_logger.info(f'User logged in: {user.username} ({user.phone}) IP={request.remote_addr}')

            next_page = request.args.get('next')
            if not next_page:
                next_page = url_for('main.index')

            flash(f'欢迎回来，{user.username}！', 'success')
            return redirect(next_page)
        else:
            audit_logger.warning(f'Failed login attempt for: {username} IP={request.remote_addr}')
            flash('用户名或密码错误', 'danger')

    return render_template('auth/login.html')


@bp.route('/logout')
@login_required
def logout():
    """退出登录"""
    audit_logger.info(f'User logged out: {current_user.username}')
    logout_user()
    flash('您已退出登录', 'info')
    return redirect(url_for('main.index'))


@bp.route('/profile')
@login_required
def profile():
    """个人中心"""
    from app.models import Clue, TaskAssignment, PointLog

    clues = Clue.query.filter_by(reporter_id=current_user.id).\
        order_by(Clue.submitted_at.desc()).limit(5).all()

    tasks = TaskAssignment.query.filter_by(user_id=current_user.id).\
        order_by(TaskAssignment.assigned_at.desc()).limit(5).all()

    point_logs = PointLog.query.filter_by(user_id=current_user.id).\
        order_by(PointLog.created_at.desc()).limit(10).all()

    return render_template('auth/profile.html',
                         clues=clues, tasks=tasks, point_logs=point_logs)


@bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    """编辑个人资料"""
    if request.method == 'POST':
        real_name = request.form.get('real_name', '').strip()
        email = request.form.get('email', '').strip()

        if email:
            valid, msg = validate_email(email)
            if not valid:
                flash(msg, 'danger')
                return redirect(url_for('auth.profile'))

        current_user.real_name = real_name
        current_user.email = email if email else None
        db.session.commit()
        flash('资料更新成功', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/edit_profile.html')


@bp.route('/password/change', methods=['POST'])
@login_required
def change_password():
    """修改密码"""
    old_password = request.form.get('old_password', '')
    new_password = request.form.get('new_password', '')
    new_password2 = request.form.get('new_password2', '')

    if not current_user.check_password(old_password):
        flash('原密码错误', 'danger')
        return redirect(url_for('auth.profile'))

    valid, msg = validate_password(new_password)
    if not valid:
        flash(msg, 'danger')
        return redirect(url_for('auth.profile'))

    if new_password != new_password2:
        flash('两次输入的新密码不一致', 'danger')
        return redirect(url_for('auth.profile'))

    current_user.set_password(new_password)
    db.session.commit()
    audit_logger.info(f'User changed password: {current_user.username}')

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
        real_name = request.form.get('real_name', '').strip()
        id_card = request.form.get('id_card', '').strip().upper()

        if not real_name:
            flash('请输入真实姓名', 'danger')
            return redirect(url_for('auth.verify_identity'))

        valid, msg = validate_id_card(id_card)
        if not valid:
            flash(msg, 'danger')
            return redirect(url_for('auth.verify_identity'))

        current_user.real_name = real_name
        current_user.id_card = id_card  # 自动加密存储
        current_user.is_verified = True
        db.session.commit()

        audit_logger.info(f'User verified identity: {current_user.username}')
        flash('实名认证成功！', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('auth/verify.html')
