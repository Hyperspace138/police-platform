# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 管理员路由
"""
from flask import Blueprint, render_template, redirect, url_for, request, flash, current_app, jsonify
from flask_login import login_required, current_user
from functools import wraps
from app import db
from app.models import (
    User, Reward, Clue, Hazard, Task, TaskAssignment,
    PatrolCheckin, EmergencyDispatch, Announcement, 
    RewardItem, PointLog, SystemConfig
)
from sqlalchemy import desc, func
from datetime import datetime, timedelta
import json

bp = Blueprint('admin', __name__)


def admin_required(f):
    """管理员权限装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role not in ['admin', 'police']:
            flash('您没有权限访问此页面', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated_function


@bp.route('/')
@login_required
@admin_required
def dashboard():
    """管理后台首页"""
    # 统计数据
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'total_users': User.query.count(),
        'new_users_today': User.query.filter(User.created_at >= today).count(),
        'total_clues': Clue.query.count(),
        'pending_clues': Clue.query.filter(Clue.status.in_(['submitted', 'reviewing'])).count(),
        'total_hazards': Hazard.query.count(),
        'pending_hazards': Hazard.query.filter_by(status='pending').count(),
        'active_rewards': Reward.query.filter_by(status='active').count(),
        'active_tasks': Task.query.filter_by(status='open').count(),
        'online_security': User.query.filter(
            User.role.in_(['security', 'grid_worker', 'cloud_sentinel']),
            User.is_on_duty == True
        ).count(),
    }
    
    # 最近待处理事项
    pending_clues = Clue.query.filter(Clue.status.in_(['submitted', 'reviewing'])).\
        order_by(Clue.submitted_at).limit(5).all()
    
    pending_hazards = Hazard.query.filter_by(status='pending').\
        order_by(Hazard.reported_at).limit(5).all()
    
    # 最近注册用户
    recent_users = User.query.order_by(desc(User.created_at)).limit(5).all()
    
    return render_template('admin/dashboard.html',
                         stats=stats,
                         pending_clues=pending_clues,
                         pending_hazards=pending_hazards,
                         recent_users=recent_users)


# ==================== 用户管理 ====================

@bp.route('/users')
@login_required
@admin_required
def users():
    """用户列表"""
    page = request.args.get('page', 1, type=int)
    role = request.args.get('role', '')
    keyword = request.args.get('keyword', '')
    
    query = User.query
    if role:
        query = query.filter_by(role=role)
    if keyword:
        query = query.filter(
            (User.username.contains(keyword)) |
            (User.phone.contains(keyword)) |
            (User.real_name.contains(keyword))
        )
    
    pagination = query.order_by(desc(User.created_at)).paginate(
        page=page, per_page=20, error_out=False
    )
    
    return render_template('admin/users.html',
                         users=pagination.items,
                         pagination=pagination,
                         roles=current_app.config['USER_ROLES'])


@bp.route('/user/<int:id>/edit', methods=['POST'])
@login_required
@admin_required
def edit_user(id):
    """编辑用户"""
    user = User.query.get_or_404(id)
    
    user.role = request.form.get('role', user.role)
    user.is_active = request.form.get('is_active') == 'on'
    user.points = request.form.get('points', user.points, type=int)
    
    db.session.commit()
    flash('用户信息已更新', 'success')
    return redirect(url_for('admin.users'))


@bp.route('/user/<int:id>/toggle-active', methods=['POST'])
@login_required
@admin_required
def toggle_user_active(id):
    """切换用户状态"""
    user = User.query.get_or_404(id)
    user.is_active = not user.is_active
    db.session.commit()
    
    return jsonify({'success': True, 'is_active': user.is_active})


# ==================== 悬赏令管理 ====================

@bp.route('/rewards')
@login_required
@admin_required
def admin_rewards():
    """悬赏令管理"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Reward.query
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(desc(Reward.published_at)).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('admin/rewards.html',
                         rewards=pagination.items,
                         pagination=pagination,
                         statuses=current_app.config['REWARD_STATUS'])


@bp.route('/reward/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_reward():
    """创建悬赏令"""
    if request.method == 'POST':
        reward = Reward(
            title=request.form.get('title'),
            content=request.form.get('content'),
            case_type=request.form.get('case_type'),
            reward_amount=request.form.get('reward_amount', 0, type=float),
            reward_type=request.form.get('reward_type', 'cash'),
            suspect_name=request.form.get('suspect_name'),
            suspect_description=request.form.get('suspect_description'),
            location=request.form.get('location'),
            lat=request.form.get('lat', type=float),
            lng=request.form.get('lng', type=float),
            published_by=current_user.id,
            status='active'
        )
        
        # 处理截止日期
        deadline = request.form.get('deadline')
        if deadline:
            reward.deadline = datetime.strptime(deadline, '%Y-%m-%d')
        
        # 处理嫌疑人照片
        if 'suspect_photo' in request.files:
            file = request.files['suspect_photo']
            if file and file.filename:
                from werkzeug.utils import secure_filename
                import os
                filename = secure_filename(file.filename)
                unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'rewards', unique_name)
                os.makedirs(os.path.dirname(file_path), exist_ok=True)
                file.save(file_path)
                reward.suspect_photo = f'uploads/rewards/{unique_name}'
        
        db.session.add(reward)
        db.session.commit()
        
        flash('悬赏令发布成功', 'success')
        return redirect(url_for('admin.admin_rewards'))
    
    return render_template('admin/create_reward.html',
                         amap_key=current_app.config['AMAP_KEY'])


@bp.route('/reward/<int:id>/edit', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_reward(id):
    """编辑悬赏令"""
    reward = Reward.query.get_or_404(id)
    
    if request.method == 'POST':
        reward.title = request.form.get('title')
        reward.content = request.form.get('content')
        reward.case_type = request.form.get('case_type')
        reward.reward_amount = request.form.get('reward_amount', 0, type=float)
        reward.status = request.form.get('status', reward.status)
        
        db.session.commit()
        flash('悬赏令已更新', 'success')
        return redirect(url_for('admin.admin_rewards'))
    
    return render_template('admin/edit_reward.html', reward=reward)


@bp.route('/reward/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_reward(id):
    """删除悬赏令"""
    reward = Reward.query.get_or_404(id)
    reward.status = 'cancelled'
    db.session.commit()
    
    flash('悬赏令已取消', 'success')
    return redirect(url_for('admin.admin_rewards'))


# ==================== 线索管理 ====================

@bp.route('/clues')
@login_required
@admin_required
def admin_clues():
    """线索管理"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Clue.query
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(desc(Clue.submitted_at)).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('admin/clues.html',
                         clues=pagination.items,
                         pagination=pagination,
                         statuses=current_app.config['CLUE_STATUS'])


@bp.route('/clue/<int:id>')
@login_required
@admin_required
def clue_detail(id):
    """线索详情"""
    clue = Clue.query.get_or_404(id)
    
    # 获取所有民警用于指派
    police_users = User.query.filter_by(role='police').all()
    
    return render_template('admin/clue_detail.html',
                         clue=clue,
                         police_users=police_users)


@bp.route('/clue/<int:id>/handle', methods=['POST'])
@login_required
@admin_required
def handle_clue(id):
    """处理线索"""
    clue = Clue.query.get_or_404(id)
    
    action = request.form.get('action')
    notes = request.form.get('notes', '')
    assigned_to = request.form.get('assigned_to', type=int)
    
    if action == 'review':
        clue.status = 'reviewing'
        clue.reviewed_at = datetime.utcnow()
    elif action == 'investigate':
        clue.status = 'investigating'
        if assigned_to:
            clue.assigned_to = assigned_to
    elif action == 'verify':
        clue.status = 'verified'
    elif action == 'close':
        clue.status = 'closed'
        clue.completed_at = datetime.utcnow()
    elif action == 'reward':
        clue.status = 'rewarded'
        clue.reward_given = request.form.get('reward_amount', 0, type=float)
        clue.reward_points = request.form.get('reward_points', 0, type=int)
        clue.completed_at = datetime.utcnow()
        
        # 给举报人增加积分
        if clue.reporter_id:
            reporter = User.query.get(clue.reporter_id)
            if reporter:
                reporter.add_points(clue.reward_points, '线索被采纳奖励')
    
    clue.handler_notes = notes
    db.session.commit()
    
    flash('线索处理状态已更新', 'success')
    return redirect(url_for('admin.clue_detail', id=id))


# ==================== 隐患管理 ====================

@bp.route('/hazards')
@login_required
@admin_required
def admin_hazards():
    """隐患管理"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Hazard.query
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(desc(Hazard.reported_at)).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('admin/hazards.html',
                         hazards=pagination.items,
                         pagination=pagination)


@bp.route('/hazard/<int:id>/handle', methods=['POST'])
@login_required
@admin_required
def handle_hazard(id):
    """处理隐患"""
    hazard = Hazard.query.get_or_404(id)
    
    action = request.form.get('action')
    notes = request.form.get('notes', '')
    
    if action == 'process':
        hazard.status = 'processing'
        hazard.handler_id = current_user.id
    elif action == 'resolve':
        hazard.status = 'resolved'
        hazard.resolved_at = datetime.utcnow()
        
        # 给举报人增加积分
        if hazard.reporter_id:
            reporter = User.query.get(hazard.reporter_id)
            if reporter:
                reporter.add_points(20, '隐患被解决奖励')
    elif action == 'ignore':
        hazard.status = 'ignored'
    
    hazard.handle_notes = notes
    db.session.commit()
    
    flash('隐患处理状态已更新', 'success')
    return redirect(url_for('admin.admin_hazards'))


# ==================== 任务管理 ====================

@bp.route('/tasks')
@login_required
@admin_required
def admin_tasks():
    """任务管理"""
    page = request.args.get('page', 1, type=int)
    status = request.args.get('status', '')
    
    query = Task.query
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(desc(Task.published_at)).paginate(
        page=page, per_page=15, error_out=False
    )
    
    return render_template('admin/tasks.html',
                         tasks=pagination.items,
                         pagination=pagination)


@bp.route('/task/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_task():
    """创建任务"""
    if request.method == 'POST':
        task = Task(
            title=request.form.get('title'),
            description=request.form.get('description'),
            task_type=request.form.get('task_type'),
            location=request.form.get('location'),
            lat=request.form.get('lat', type=float),
            lng=request.form.get('lng', type=float),
            radius=request.form.get('radius', 500, type=int),
            reward_points=request.form.get('reward_points', 0, type=int),
            reward_cash=request.form.get('reward_cash', 0, type=float),
            required_people=request.form.get('required_people', 1, type=int),
            published_by=current_user.id
        )
        
        # 处理时间
        start_time = request.form.get('start_time')
        end_time = request.form.get('end_time')
        if start_time:
            task.start_time = datetime.strptime(start_time, '%Y-%m-%dT%H:%M')
        if end_time:
            task.end_time = datetime.strptime(end_time, '%Y-%m-%dT%H:%M')
        
        db.session.add(task)
        db.session.commit()
        
        flash('任务发布成功', 'success')
        return redirect(url_for('admin.admin_tasks'))
    
    return render_template('admin/create_task.html',
                         amap_key=current_app.config['AMAP_KEY'])


@bp.route('/task/<int:id>/verify', methods=['POST'])
@login_required
@admin_required
def verify_task(id):
    """审核任务完成"""
    assignment = TaskAssignment.query.get_or_404(id)
    
    is_approved = request.form.get('is_approved') == 'on'
    
    if is_approved:
        assignment.is_verified = True
        assignment.verified_by = current_user.id
        assignment.verified_at = datetime.utcnow()
        
        # 给完成任务的用户增加积分
        assignee = User.query.get(assignment.user_id)
        if assignee:
            assignee.add_points(
                assignment.task.reward_points,
                f'完成任务：{assignment.task.title}'
            )
        
        flash('任务审核通过', 'success')
    else:
        assignment.status = 'assigned'
        flash('任务审核不通过，已退回', 'warning')
    
    db.session.commit()
    return redirect(url_for('admin.admin_tasks'))


# ==================== 应急调度 ====================

@bp.route('/emergency')
@login_required
@admin_required
def emergency_dispatch():
    """应急调度"""
    # 获取在线安保人员
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    online_security = User.query.filter(
        User.role.in_(['security', 'grid_worker', 'cloud_sentinel']),
        User.last_checkin >= one_hour_ago
    ).all()
    
    # 获取进行中的应急事件
    active_emergencies = EmergencyDispatch.query.filter(
        EmergencyDispatch.status.in_(['dispatching', 'responding'])
    ).all()
    
    return render_template('admin/emergency.html',
                         online_security=online_security,
                         active_emergencies=active_emergencies,
                         amap_key=current_app.config['AMAP_KEY'])


@bp.route('/emergency/create', methods=['POST'])
@login_required
@admin_required
def create_emergency():
    """创建应急调度"""
    emergency = EmergencyDispatch(
        title=request.form.get('title'),
        description=request.form.get('description'),
        emergency_type=request.form.get('emergency_type'),
        location=request.form.get('location'),
        lat=request.form.get('lat', type=float),
        lng=request.form.get('lng', type=float),
        urgency=request.form.get('urgency', 'high'),
        dispatch_radius=request.form.get('dispatch_radius', 1000, type=int),
        dispatched_by=current_user.id
    )
    
    db.session.add(emergency)
    db.session.commit()
    
    flash('应急调度已发起', 'success')
    return redirect(url_for('admin.emergency_dispatch'))


@bp.route('/emergency/<int:id>/resolve', methods=['POST'])
@login_required
@admin_required
def resolve_emergency(id):
    """解决应急事件"""
    emergency = EmergencyDispatch.query.get_or_404(id)
    
    emergency.status = 'resolved'
    emergency.resolved_at = datetime.utcnow()
    emergency.resolution_notes = request.form.get('resolution_notes', '')
    
    db.session.commit()
    
    flash('应急事件已标记为已解决', 'success')
    return redirect(url_for('admin.emergency_dispatch'))


# ==================== 公告管理 ====================

@bp.route('/announcements')
@login_required
@admin_required
def admin_announcements():
    """公告管理"""
    page = request.args.get('page', 1, type=int)
    
    pagination = Announcement.query.order_by(
        desc(Announcement.is_pinned),
        desc(Announcement.published_at)
    ).paginate(page=page, per_page=15, error_out=False)
    
    return render_template('admin/announcements.html',
                         announcements=pagination.items,
                         pagination=pagination)


@bp.route('/announcement/create', methods=['GET', 'POST'])
@login_required
@admin_required
def create_announcement():
    """创建公告"""
    if request.method == 'POST':
        announcement = Announcement(
            title=request.form.get('title'),
            content=request.form.get('content'),
            category=request.form.get('category', 'notice'),
            is_pinned=request.form.get('is_pinned') == 'on',
            published_by=current_user.id
        )
        
        db.session.add(announcement)
        db.session.commit()
        
        flash('公告发布成功', 'success')
        return redirect(url_for('admin.admin_announcements'))
    
    return render_template('admin/create_announcement.html')


@bp.route('/announcement/<int:id>/delete', methods=['POST'])
@login_required
@admin_required
def delete_announcement(id):
    """删除公告"""
    announcement = Announcement.query.get_or_404(id)
    db.session.delete(announcement)
    db.session.commit()
    
    flash('公告已删除', 'success')
    return redirect(url_for('admin.admin_announcements'))


# ==================== 积分商城管理 ====================

@bp.route('/reward-items')
@login_required
@admin_required
def reward_items():
    """积分商品管理"""
    items = RewardItem.query.all()
    return render_template('admin/reward_items.html', items=items)


@bp.route('/reward-item/create', methods=['POST'])
@login_required
@admin_required
def create_reward_item():
    """创建积分商品"""
    item = RewardItem(
        name=request.form.get('name'),
        description=request.form.get('description'),
        required_points=request.form.get('required_points', 0, type=int),
        stock=request.form.get('stock', 0, type=int)
    )
    
    db.session.add(item)
    db.session.commit()
    
    flash('商品添加成功', 'success')
    return redirect(url_for('admin.reward_items'))


# ==================== 系统设置 ====================

@bp.route('/settings')
@login_required
@admin_required
def settings():
    """系统设置"""
    configs = SystemConfig.query.all()
    return render_template('admin/settings.html', configs=configs)


@bp.route('/setting/update', methods=['POST'])
@login_required
@admin_required
def update_setting():
    """更新系统设置"""
    key = request.form.get('key')
    value = request.form.get('value')
    
    config = SystemConfig.query.filter_by(key=key).first()
    if config:
        config.value = value
    else:
        config = SystemConfig(key=key, value=value)
        db.session.add(config)
    
    db.session.commit()
    
    return jsonify({'success': True})
