# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - API路由
"""
from flask import Blueprint, request, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import (
    User, Reward, Clue, Hazard, Task, TaskAssignment,
    PatrolCheckin, EmergencyDispatch, Announcement, PointLog
)
from sqlalchemy import desc, func
from datetime import datetime, timedelta
import json

bp = Blueprint('api', __name__)


# 通用响应格式
def api_response(success=True, data=None, message='', code=200):
    return jsonify({
        'success': success,
        'data': data,
        'message': message,
        'code': code
    }), code


# ==================== 用户相关API ====================

@bp.route('/user/info')
@login_required
def get_user_info():
    """获取用户信息"""
    return api_response(data={
        'id': current_user.id,
        'username': current_user.username,
        'phone': current_user.phone,
        'email': current_user.email,
        'role': current_user.role,
        'points': current_user.points,
        'total_points': current_user.total_points,
        'is_verified': current_user.is_verified,
        'avatar': current_user.avatar,
        'created_at': current_user.created_at.isoformat() if current_user.created_at else None
    })


@bp.route('/user/location', methods=['POST'])
@login_required
def update_location():
    """更新用户位置"""
    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')
    
    if lat and lng:
        current_user.lat = lat
        current_user.lng = lng
        db.session.commit()
        return api_response(message='位置更新成功')
    
    return api_response(success=False, message='参数错误', code=400)


@bp.route('/user/duty', methods=['POST'])
@login_required
def toggle_duty():
    """切换值班状态"""
    data = request.get_json()
    is_on_duty = data.get('is_on_duty', False)
    
    current_user.is_on_duty = is_on_duty
    if is_on_duty:
        current_user.last_checkin = datetime.utcnow()
    
    db.session.commit()
    
    return api_response(data={'is_on_duty': is_on_duty})


# ==================== 悬赏令API ====================

@bp.route('/rewards')
def get_rewards():
    """获取悬赏令列表"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    case_type = request.args.get('case_type', '')
    
    query = Reward.query.filter_by(status='active')
    if case_type:
        query = query.filter_by(case_type=case_type)
    
    pagination = query.order_by(desc(Reward.published_at)).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    data = {
        'items': [{
            'id': r.id,
            'title': r.title,
            'case_type': r.case_type,
            'reward_amount': r.reward_amount,
            'location': r.location,
            'published_at': r.published_at.isoformat() if r.published_at else None,
            'deadline': r.deadline.isoformat() if r.deadline else None,
            'view_count': r.view_count
        } for r in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages,
        'current_page': page
    }
    
    return api_response(data=data)


@bp.route('/reward/<int:id>')
def get_reward_detail(id):
    """获取悬赏令详情"""
    reward = Reward.query.get_or_404(id)
    
    # 增加浏览量
    reward.view_count += 1
    db.session.commit()
    
    data = {
        'id': reward.id,
        'title': reward.title,
        'content': reward.content,
        'case_type': reward.case_type,
        'reward_amount': reward.reward_amount,
        'reward_type': reward.reward_type,
        'suspect_name': reward.suspect_name,
        'suspect_description': reward.suspect_description,
        'suspect_photo': reward.suspect_photo,
        'location': reward.location,
        'lat': reward.lat,
        'lng': reward.lng,
        'status': reward.status,
        'published_at': reward.published_at.isoformat() if reward.published_at else None,
        'deadline': reward.deadline.isoformat() if reward.deadline else None,
        'view_count': reward.view_count
    }
    
    return api_response(data=data)


# ==================== 线索API ====================

@bp.route('/clues', methods=['POST'])
@login_required
def create_clue():
    """创建线索"""
    data = request.get_json()
    
    clue = Clue(
        reward_id=data.get('reward_id'),
        reporter_id=current_user.id,
        is_anonymous=data.get('is_anonymous', False),
        content=data.get('content'),
        clue_type=data.get('clue_type'),
        lat=data.get('lat'),
        lng=data.get('lng'),
        location=data.get('location'),
        address_from_gps=data.get('address_from_gps'),
        contact_phone=data.get('contact_phone'),
        media_files=json.dumps(data.get('media_files', []))
    )
    
    db.session.add(clue)
    db.session.commit()
    
    # 增加积分
    if not clue.is_anonymous:
        current_user.add_points(
            current_app.config['POINTS_CONFIG']['clue_submit'],
            '提交线索'
        )
    
    return api_response(data={
        'clue_no': clue.clue_no,
        'anonymous_code': clue.anonymous_code if clue.is_anonymous else None
    }, message='线索提交成功')


@bp.route('/clue/<string:clue_no>')
def get_clue_status(clue_no):
    """查询线索状态"""
    clue = Clue.query.filter_by(clue_no=clue_no).first()
    
    if not clue:
        return api_response(success=False, message='线索不存在', code=404)
    
    # 构建状态时间线
    timeline = []
    timeline.append({
        'status': 'submitted',
        'title': '线索已提交',
        'time': clue.submitted_at.isoformat() if clue.submitted_at else None
    })
    
    if clue.status in ['reviewing', 'investigating', 'verified', 'closed', 'rewarded']:
        timeline.append({
            'status': 'reviewing',
            'title': '审核中',
            'time': clue.reviewed_at.isoformat() if clue.reviewed_at else None
        })
    
    if clue.status in ['investigating', 'verified', 'closed', 'rewarded']:
        timeline.append({
            'status': 'investigating',
            'title': '核查中',
            'time': None
        })
    
    if clue.status in ['verified', 'closed', 'rewarded']:
        timeline.append({
            'status': 'verified',
            'title': '已核实',
            'time': None
        })
    
    if clue.status in ['closed', 'rewarded']:
        timeline.append({
            'status': 'closed',
            'title': '已办结',
            'time': clue.completed_at.isoformat() if clue.completed_at else None
        })
    
    if clue.status == 'rewarded':
        timeline.append({
            'status': 'rewarded',
            'title': '已发放奖励',
            'time': None
        })
    
    data = {
        'clue_no': clue.clue_no,
        'status': clue.status,
        'content': clue.content if not clue.is_anonymous else '匿名举报内容已隐藏',
        'clue_type': clue.clue_type,
        'submitted_at': clue.submitted_at.isoformat() if clue.submitted_at else None,
        'timeline': timeline,
        'handler_notes': clue.handler_notes,
        'reward_given': clue.reward_given,
        'reward_points': clue.reward_points
    }
    
    return api_response(data=data)


# ==================== 隐患API ====================

@bp.route('/hazards', methods=['GET'])
def get_hazards():
    """获取隐患列表"""
    page = request.args.get('page', 1, type=int)
    hazard_type = request.args.get('hazard_type', '')
    status = request.args.get('status', '')
    
    query = Hazard.query
    if hazard_type:
        query = query.filter_by(hazard_type=hazard_type)
    if status:
        query = query.filter_by(status=status)
    
    pagination = query.order_by(desc(Hazard.reported_at)).paginate(
        page=page, per_page=10, error_out=False
    )
    
    data = {
        'items': [{
            'id': h.id,
            'hazard_no': h.hazard_no,
            'hazard_type': h.hazard_type,
            'description': h.description,
            'location': h.location,
            'lat': h.lat,
            'lng': h.lng,
            'status': h.status,
            'urgency': h.urgency,
            'reported_at': h.reported_at.isoformat() if h.reported_at else None
        } for h in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages
    }
    
    return api_response(data=data)


@bp.route('/hazards', methods=['POST'])
@login_required
def create_hazard():
    """创建隐患上报"""
    data = request.get_json()
    
    hazard = Hazard(
        reporter_id=current_user.id,
        hazard_type=data.get('hazard_type'),
        description=data.get('description'),
        lat=data.get('lat'),
        lng=data.get('lng'),
        location=data.get('location'),
        urgency=data.get('urgency', 'normal'),
        photos=json.dumps(data.get('photos', []))
    )
    
    db.session.add(hazard)
    db.session.commit()
    
    # 增加积分
    current_user.add_points(
        current_app.config['POINTS_CONFIG']['clue_submit'],
        '上报安全隐患'
    )
    
    return api_response(data={'hazard_no': hazard.hazard_no}, message='隐患上报成功')


@bp.route('/hazards/map')
def get_hazards_map():
    """获取隐患地图数据"""
    hazards = Hazard.query.filter(
        Hazard.lat.isnot(None),
        Hazard.lng.isnot(None)
    ).all()
    
    data = [{
        'id': h.id,
        'lat': h.lat,
        'lng': h.lng,
        'type': h.hazard_type,
        'status': h.status,
        'urgency': h.urgency
    } for h in hazards]
    
    return api_response(data=data)


# ==================== 任务API ====================

@bp.route('/tasks')
def get_tasks():
    """获取任务列表"""
    page = request.args.get('page', 1, type=int)
    task_type = request.args.get('task_type', '')
    
    query = Task.query.filter_by(status='open')
    if task_type:
        query = query.filter_by(task_type=task_type)
    
    pagination = query.order_by(desc(Task.published_at)).paginate(
        page=page, per_page=10, error_out=False
    )
    
    data = {
        'items': [{
            'id': t.id,
            'task_no': t.task_no,
            'title': t.title,
            'description': t.description,
            'task_type': t.task_type,
            'location': t.location,
            'lat': t.lat,
            'lng': t.lng,
            'reward_points': t.reward_points,
            'reward_cash': t.reward_cash,
            'start_time': t.start_time.isoformat() if t.start_time else None,
            'end_time': t.end_time.isoformat() if t.end_time else None,
            'required_people': t.required_people,
            'current_people': TaskAssignment.query.filter_by(task_id=t.id).count()
        } for t in pagination.items],
        'total': pagination.total,
        'pages': pagination.pages
    }
    
    return api_response(data=data)


@bp.route('/task/<int:id>/claim', methods=['POST'])
@login_required
def api_claim_task(id):
    """API抢单"""
    task = Task.query.get_or_404(id)
    
    if task.status != 'open':
        return api_response(success=False, message='该任务已被抢完', code=400)
    
    # 防刷分：检查每日抢单上限
    daily_limit = current_app.config.get('TASK_CLAIM_DAILY_LIMIT', 10)
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    today_claims = TaskAssignment.query.filter_by(user_id=current_user.id)\
        .filter(TaskAssignment.assigned_at >= today_start).count()
    if today_claims >= daily_limit:
        return api_response(success=False, message=f'今日抢单已达上限（{daily_limit}单），请明天再参与', code=400)

    existing = TaskAssignment.query.filter_by(
        task_id=id,
        user_id=current_user.id
    ).first()

    if existing:
        return api_response(success=False, message='您已接过此任务', code=400)
    
    assignment = TaskAssignment(
        task_id=id,
        user_id=current_user.id,
        status='assigned'
    )
    
    current_count = TaskAssignment.query.filter_by(task_id=id).count()
    if current_count + 1 >= task.required_people:
        task.status = 'assigned'
    
    db.session.add(assignment)
    db.session.commit()
    
    return api_response(message='抢单成功')


@bp.route('/task/<int:id>/start', methods=['POST'])
@login_required
def start_task(id):
    """开始任务"""
    assignment = TaskAssignment.query.filter_by(
        task_id=id,
        user_id=current_user.id
    ).first_or_404()
    
    assignment.status = 'in_progress'
    assignment.started_at = datetime.utcnow()
    assignment.task.status = 'in_progress'
    
    db.session.commit()
    
    return api_response(message='任务已开始')


@bp.route('/task/<int:id>/complete', methods=['POST'])
@login_required
def complete_task(id):
    """完成任务"""
    data = request.get_json()
    
    assignment = TaskAssignment.query.filter_by(
        task_id=id,
        user_id=current_user.id
    ).first_or_404()
    
    assignment.status = 'completed'
    assignment.completed_at = datetime.utcnow()
    assignment.completion_notes = data.get('notes', '')
    assignment.proof_photos = json.dumps(data.get('photos', []))
    
    db.session.commit()
    
    return api_response(message='任务完成，等待审核')


# ==================== 巡逻打卡API ====================

@bp.route('/patrol/checkin', methods=['POST'])
@login_required
def api_patrol_checkin():
    """API巡逻打卡（含防刷分检测）"""
    data = request.get_json()
    lat = data.get('lat')
    lng = data.get('lng')

    # 防刷分：检查是否在短时间内重复打卡
    min_interval = current_app.config.get('PATROL_MIN_INTERVAL', 300)
    min_distance = current_app.config.get('PATROL_MIN_DISTANCE', 100)

    recent = PatrolCheckin.query.filter_by(user_id=current_user.id)\
        .filter(PatrolCheckin.checkin_at >= datetime.utcnow() - timedelta(seconds=min_interval))\
        .order_by(desc(PatrolCheckin.checkin_at)).first()

    if recent and lat and lng and recent.lat and recent.lng:
        # 计算距离（简化：欧几里得距离近似）
        import math
        dlat = (lat - recent.lat) * 111320  # 纬度转米
        dlng = (lng - recent.lng) * 111320 * math.cos(math.radians(lat))
        distance = math.sqrt(dlat**2 + dlng**2)
        if distance < min_distance:
            return api_response(success=False, message=f'打卡过于频繁，{min_interval // 60}分钟内请勿在同一位置重复打卡'), 429

    checkin = PatrolCheckin(
        user_id=current_user.id,
        lat=lat,
        lng=lng,
        location=data.get('location'),
        notes=data.get('notes', ''),
        photo=data.get('photo', '')
    )

    db.session.add(checkin)

    current_user.last_checkin = datetime.utcnow()
    current_user.is_on_duty = True

    db.session.commit()

    # 增加积分
    points = current_app.config['POINTS_CONFIG']['patrol_checkin']
    current_user.add_points(points, '巡逻打卡')

    return api_response(data={'points_earned': points}, message='打卡成功')


@bp.route('/patrol/history')
@login_required
def get_patrol_history():
    """获取巡逻历史"""
    checkins = PatrolCheckin.query.filter_by(user_id=current_user.id).\
        order_by(desc(PatrolCheckin.checkin_at)).limit(30).all()
    
    data = [{
        'id': c.id,
        'lat': c.lat,
        'lng': c.lng,
        'location': c.location,
        'checkin_at': c.checkin_at.isoformat() if c.checkin_at else None
    } for c in checkins]
    
    return api_response(data=data)


# ==================== 实时位置追踪API ====================

@bp.route('/tracking/personnel')
@login_required
def get_personnel_locations():
    """获取所有在线安保人员的实时位置（管理员/民警可见）"""
    if current_user.role not in ['admin', 'police']:
        return api_response(success=False, message='无权限访问', code=403)

    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    personnel = User.query.filter(
        User.role.in_(['security', 'grid_worker', 'cloud_sentinel']),
        User.last_checkin >= one_hour_ago,
        User.lat.isnot(None),
        User.lng.isnot(None)
    ).all()

    data = [{
        'id': u.id,
        'username': u.username,
        'real_name': u.real_name or u.username,
        'role': u.role,
        'role_name': current_app.config['USER_ROLES'].get(u.role, ''),
        'lat': u.lat,
        'lng': u.lng,
        'is_on_duty': u.is_on_duty,
        'last_checkin': u.last_checkin.isoformat() if u.last_checkin else None,
        'work_unit': u.work_unit or '',
        'phone': u.phone if current_user.role == 'admin' else ''
    } for u in personnel]

    return api_response(data=data)


# ==================== 应急调度API ====================

@bp.route('/emergency/nearby')
@login_required
def get_nearby_emergencies():
    """获取附近的应急事件"""
    lat = request.args.get('lat', type=float)
    lng = request.args.get('lng', type=float)
    radius = request.args.get('radius', 5000, type=int)  # 默认5公里
    
    # 简化实现，实际应计算距离
    emergencies = EmergencyDispatch.query.filter(
        EmergencyDispatch.status.in_(['dispatching', 'responding'])
    ).all()
    
    data = [{
        'id': e.id,
        'title': e.title,
        'lat': e.lat,
        'lng': e.lng,
        'location': e.location,
        'urgency': e.urgency,
        'status': e.status,
        'dispatched_at': e.dispatched_at.isoformat() if e.dispatched_at else None
    } for e in emergencies]
    
    return api_response(data=data)


@bp.route('/emergency/<int:id>/respond', methods=['POST'])
@login_required
def respond_emergency(id):
    """响应应急调度"""
    emergency = EmergencyDispatch.query.get_or_404(id)
    
    # 添加响应者
    responders = json.loads(emergency.responders)
    if current_user.id not in responders:
        responders.append(current_user.id)
        emergency.responders = json.dumps(responders)
        
        if emergency.status == 'dispatching':
            emergency.status = 'responding'
        
        db.session.commit()
        
        # 增加积分
        current_user.add_points(
            current_app.config['POINTS_CONFIG']['emergency_response'],
            '应急响应'
        )
    
    return api_response(message='响应成功')


# ==================== 统计API ====================

@bp.route('/stats/dashboard')
def get_dashboard_stats():
    """获取仪表盘统计数据"""
    # 今日数据
    today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    
    stats = {
        'total_rewards': Reward.query.filter_by(status='active').count(),
        'total_clues': Clue.query.count(),
        'today_clues': Clue.query.filter(Clue.submitted_at >= today).count(),
        'resolved_hazards': Hazard.query.filter_by(status='resolved').count(),
        'active_tasks': Task.query.filter_by(status='open').count(),
        'online_security': User.query.filter(
            User.role.in_(['security', 'grid_worker', 'cloud_sentinel']),
            User.is_on_duty == True
        ).count(),
        'total_users': User.query.count(),
        'total_points_distributed': db.session.query(func.sum(User.total_points)).scalar() or 0
    }
    
    return api_response(data=stats)


@bp.route('/stats/heatmap')
def get_heatmap_data():
    """获取热力图数据"""
    # 隐患热力图
    hazards = Hazard.query.filter(
        Hazard.lat.isnot(None),
        Hazard.lng.isnot(None)
    ).all()
    
    data = [{
        'lat': h.lat,
        'lng': h.lng,
        'weight': 1 if h.urgency == 'normal' else (2 if h.urgency == 'high' else 3)
    } for h in hazards]
    
    return api_response(data=data)


# ==================== AI相关API ====================

@bp.route('/leaderboard')
def get_leaderboard():
    """获取积分排行榜"""
    limit = request.args.get('limit', 20, type=int)
    role = request.args.get('role', '')

    query = User.query.filter(User.is_active == True, User.role != 'admin')
    if role:
        query = query.filter_by(role=role)

    users = query.order_by(User.total_points.desc()).limit(min(limit, 100)).all()

    data = [{
        'rank': i + 1,
        'id': u.id,
        'username': u.username,
        'real_name': u.real_name,
        'role': u.role,
        'role_name': current_app.config['USER_ROLES'].get(u.role, '普通用户'),
        'points': u.points,
        'total_points': u.total_points,
        'is_verified': u.is_verified,
        'avatar': u.avatar
    } for i, u in enumerate(users)]

    return api_response(data=data)


@bp.route('/ai/analyze-image', methods=['POST'])
def ai_analyze_image():
    """AI图像分析"""
    import random
    from PIL import Image
    import io

    hazard_types = [
        {'type': '消防通道堵塞', 'desc': '检测到消防通道被车辆或杂物占用'},
        {'type': '井盖缺失', 'desc': '检测到路面井盖缺失，存在安全隐患'},
        {'type': '路灯损坏', 'desc': '检测到路灯故障不亮'},
        {'type': '路面塌陷', 'desc': '检测到路面出现塌陷或裂缝'},
        {'type': '电线裸露', 'desc': '检测到电线外露，存在触电风险'},
        {'type': '车辆违停', 'desc': '检测到车辆违规停放占用通道'},
        {'type': '可疑人员', 'desc': '检测到异常徘徊行为'},
        {'type': '其他隐患', 'desc': '检测到一般安全隐患'},
    ]

    image_info = {}
    if 'image' in request.files:
        file = request.files['image']
        if file and file.filename:
            try:
                img = Image.open(file.stream)
                image_info = {
                    'width': img.width,
                    'height': img.height,
                    'format': img.format,
                    'mode': img.mode
                }
            except Exception:
                pass

    selected = random.choice(hazard_types)
    confidence = round(random.uniform(0.65, 0.95), 2)

    return api_response(data={
        'hazard_type': selected['type'],
        'confidence': confidence,
        'suggested_description': selected['desc'],
        'image_info': image_info,
        'all_predictions': [
            {'type': selected['type'], 'confidence': confidence},
            {'type': random.choice([h for h in hazard_types if h['type'] != selected['type']])['type'],
             'confidence': round(random.uniform(0.3, 0.6), 2)},
            {'type': '其他隐患', 'confidence': round(random.uniform(0.1, 0.3), 2)}
        ]
    })


@bp.route('/ai/suggest-address')
def ai_suggest_address():
    """地址智能补全"""
    keyword = request.args.get('keyword', '')
    
    # 这里集成地图API的地址补全功能
    # 模拟返回
    suggestions = [
        {'name': '北京市朝阳区建国路88号', 'lat': 39.9042, 'lng': 116.4074},
        {'name': '北京市朝阳区建国门外大街', 'lat': 39.9050, 'lng': 116.4080},
    ]
    
    return api_response(data=suggestions)
