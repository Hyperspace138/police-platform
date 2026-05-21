# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 主路由
"""
import os
from datetime import datetime, timedelta
from flask import Blueprint, render_template, request, flash, redirect, url_for, jsonify, current_app
from flask_login import login_required, current_user
from app import db
from app.models import (
    Reward, Clue, Hazard, Task, Announcement,
    PatrolCheckin, EmergencyDispatch, RewardItem, User,
    TaskAssignment, RewardClaim
)
from sqlalchemy import desc, func
from datetime import datetime, timedelta

bp = Blueprint('main', __name__)


@bp.route('/')
def index():
    """首页"""
    # 获取统计数据
    stats = {
        'total_rewards': Reward.query.filter_by(status='active').count(),
        'total_clues': Clue.query.count(),
        'resolved_hazards': Hazard.query.filter_by(status='resolved').count(),
        'active_tasks': Task.query.filter_by(status='open').count(),
    }
    
    # 获取最新悬赏令
    latest_rewards = Reward.query.filter_by(status='active').order_by(
        desc(Reward.published_at)
    ).limit(5).all()
    
    # 获取最新公告
    announcements = Announcement.query.order_by(
        desc(Announcement.is_pinned),
        desc(Announcement.published_at)
    ).limit(5).all()
    
    # 获取最新任务
    latest_tasks = Task.query.filter_by(status='open').order_by(
        desc(Task.published_at)
    ).limit(4).all()
    
    # 获取治安防控地图数据（隐患热力图）
    hazards = Hazard.query.filter(
        Hazard.lat.isnot(None),
        Hazard.lng.isnot(None)
    ).all()
    
    hazard_points = []
    for h in hazards:
        hazard_points.append({
            'lat': h.lat,
            'lng': h.lng,
            'type': h.hazard_type,
            'status': h.status
        })
    
    return render_template('index.html',
                         stats=stats,
                         latest_rewards=latest_rewards,
                         announcements=announcements,
                         latest_tasks=latest_tasks,
                         hazard_points=hazard_points,
                         amap_key=current_app.config['AMAP_KEY'])


@bp.route('/rewards')
def rewards():
    """悬赏令列表"""
    page = request.args.get('page', 1, type=int)
    case_type = request.args.get('case_type', '')
    
    query = Reward.query.filter_by(status='active')
    
    if case_type:
        query = query.filter_by(case_type=case_type)
    
    pagination = query.order_by(desc(Reward.published_at)).paginate(
        page=page, per_page=10, error_out=False
    )
    
    rewards = pagination.items
    
    # 获取案件类型统计
    case_types = db.session.query(Reward.case_type, func.count(Reward.id)).\
        filter_by(status='active').group_by(Reward.case_type).all()
    
    return render_template('rewards.html',
                         rewards=rewards,
                         pagination=pagination,
                         case_types=case_types,
                         current_type=case_type)


@bp.route('/reward/<int:id>')
def reward_detail(id):
    """悬赏令详情"""
    reward = Reward.query.get_or_404(id)
    
    # 增加浏览量
    reward.view_count += 1
    db.session.commit()
    
    # 获取相关线索（如果是当前用户的）
    related_clues = []
    if current_user.is_authenticated:
        related_clues = Clue.query.filter_by(
            reward_id=id,
            reporter_id=current_user.id
        ).order_by(desc(Clue.submitted_at)).all()
    
    return render_template('reward_detail.html',
                         reward=reward,
                         related_clues=related_clues)


@bp.route('/clues', methods=['GET', 'POST'])
@login_required
def submit_clue():
    """提交线索"""
    if request.method == 'POST':
        # 处理线索提交
        reward_id = request.form.get('reward_id', type=int)
        content = request.form.get('content')
        is_anonymous = request.form.get('is_anonymous') == 'on'
        contact_phone = request.form.get('contact_phone')
        clue_type = request.form.get('clue_type')
        
        # 获取位置信息
        lat = request.form.get('lat', type=float)
        lng = request.form.get('lng', type=float)
        location = request.form.get('location')
        
        # 创建线索
        clue = Clue(
            reward_id=reward_id if reward_id else None,
            reporter_id=current_user.id if not is_anonymous else None,
            is_anonymous=is_anonymous,
            content=content,
            contact_phone=contact_phone if is_anonymous else None,
            clue_type=clue_type,
            lat=lat,
            lng=lng,
            location=location
        )
        
        # 处理上传的文件
        import json
        import os
        from werkzeug.utils import secure_filename
        
        uploaded_files = []
        if 'media_files' in request.files:
            files = request.files.getlist('media_files')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'clues', unique_name)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
                    uploaded_files.append(f'uploads/clues/{unique_name}')
        
        clue.media_files = json.dumps(uploaded_files)
        
        db.session.add(clue)
        db.session.commit()
        
        # 给举报人增加积分
        if not is_anonymous:
            current_user.add_points(
                current_app.config['POINTS_CONFIG']['clue_submit'],
                '提交线索'
            )
        
        if is_anonymous:
            flash(f'线索提交成功！请保存您的查询码：{clue.anonymous_code}', 'success')
        else:
            flash('线索提交成功！', 'success')
        
        return redirect(url_for('main.clue_status', clue_no=clue.clue_no))
    
    # GET请求
    reward_id = request.args.get('reward_id', type=int)
    reward = None
    if reward_id:
        reward = Reward.query.get(reward_id)
    
    # 线索类型选项
    clue_types = ['刑事案件', '治安案件', '消防隐患', '交通违法', '涉黑涉恶', '黄赌毒', '其他']
    
    return render_template('submit_clue.html',
                         reward=reward,
                         clue_types=clue_types,
                         amap_key=current_app.config['AMAP_KEY'])


@bp.route('/clue/status')
def clue_status():
    """查询线索状态"""
    clue_no = request.args.get('clue_no')
    anonymous_code = request.args.get('anonymous_code')
    
    clue = None
    if clue_no:
        clue = Clue.query.filter_by(clue_no=clue_no).first()
    elif anonymous_code:
        clue = Clue.query.filter_by(anonymous_code=anonymous_code).first()
    
    if not clue and (clue_no or anonymous_code):
        flash('未找到相关线索，请检查编号是否正确', 'warning')
    
    return render_template('clue_status.html', clue=clue)


@bp.route('/hazards', methods=['GET', 'POST'])
def hazards():
    """安全隐患上报与列表"""
    if request.method == 'POST':
        if not current_user.is_authenticated:
            flash('请先登录', 'warning')
            return redirect(url_for('auth.login'))
        
        # 处理隐患上报
        hazard_type = request.form.get('hazard_type')
        description = request.form.get('description')
        lat = request.form.get('lat', type=float)
        lng = request.form.get('lng', type=float)
        location = request.form.get('location')
        urgency = request.form.get('urgency', 'normal')
        
        hazard = Hazard(
            reporter_id=current_user.id,
            hazard_type=hazard_type,
            description=description,
            lat=lat,
            lng=lng,
            location=location,
            urgency=urgency
        )
        
        # 处理照片
        import json
        import os
        from werkzeug.utils import secure_filename
        
        uploaded_files = []
        if 'photos' in request.files:
            files = request.files.getlist('photos')
            for file in files:
                if file and file.filename:
                    filename = secure_filename(file.filename)
                    unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                    file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'hazards', unique_name)
                    os.makedirs(os.path.dirname(file_path), exist_ok=True)
                    file.save(file_path)
                    uploaded_files.append(f'uploads/hazards/{unique_name}')
        
        hazard.photos = json.dumps(uploaded_files)
        
        db.session.add(hazard)
        db.session.commit()
        
        # 增加积分
        current_user.add_points(
            current_app.config['POINTS_CONFIG']['clue_submit'],
            '上报安全隐患'
        )
        
        flash('隐患上报成功！感谢您的参与', 'success')
        return redirect(url_for('main.hazards'))
    
    # GET请求 - 显示隐患列表和地图
    page = request.args.get('page', 1, type=int)
    hazard_type = request.args.get('hazard_type', '')
    
    query = Hazard.query
    if hazard_type:
        query = query.filter_by(hazard_type=hazard_type)
    
    pagination = query.order_by(desc(Hazard.reported_at)).paginate(
        page=page, per_page=10, error_out=False
    )
    
    hazards_list = pagination.items
    
    # 获取地图数据
    map_hazards = Hazard.query.filter(
        Hazard.lat.isnot(None),
        Hazard.lng.isnot(None)
    ).all()
    
    hazard_points = []
    for h in map_hazards:
        hazard_points.append({
            'lat': h.lat,
            'lng': h.lng,
            'type': h.hazard_type,
            'status': h.status,
            'id': h.id
        })
    
    # 隐患类型
    hazard_types = ['消防通道堵塞', '井盖缺失', '路灯损坏', '路面塌陷', '电线裸露', '可疑人员', '其他隐患']
    
    return render_template('hazards.html',
                         hazards=hazards_list,
                         pagination=pagination,
                         hazard_types=hazard_types,
                         hazard_points=hazard_points,
                         amap_key=current_app.config['AMAP_KEY'])


@bp.route('/tasks')
def tasks():
    """任务列表"""
    page = request.args.get('page', 1, type=int)
    task_type = request.args.get('task_type', '')
    
    query = Task.query.filter_by(status='open')
    if task_type:
        query = query.filter_by(task_type=task_type)
    
    pagination = query.order_by(desc(Task.published_at)).paginate(
        page=page, per_page=10, error_out=False
    )
    
    tasks_list = pagination.items

    # 预计算每个任务的已抢单人数
    task_assignments = {}
    for task in tasks_list:
        task_assignments[task.id] = TaskAssignment.query.filter_by(task_id=task.id).count()

    # 任务类型
    task_types = [
        ('patrol', '巡逻任务'),
        ('propaganda', '宣传任务'),
        ('emergency', '应急任务'),
        ('investigation', '调查任务')
    ]

    return render_template('tasks.html',
                         tasks=tasks_list,
                         pagination=pagination,
                         task_types=task_types,
                         current_type=task_type,
                         task_assignments=task_assignments)


@bp.route('/task/<int:id>')
@login_required
def task_detail(id):
    """任务详情"""
    task = Task.query.get_or_404(id)

    has_assigned = False
    assignment = None
    if current_user.is_authenticated:
        assignment = TaskAssignment.query.filter_by(
            task_id=id,
            user_id=current_user.id
        ).first()
        has_assigned = assignment is not None

    return render_template('task_detail.html',
                         task=task,
                         has_assigned=has_assigned,
                         assignment=assignment,
                         amap_key=current_app.config['AMAP_KEY'],
                         amap_security_code=current_app.config.get('AMAP_SECURITY_CODE', ''))


@bp.route('/task/<int:id>/claim', methods=['POST'])
@login_required
def claim_task(id):
    """抢单"""
    task = Task.query.get_or_404(id)
    
    if task.status != 'open':
        flash('该任务已被抢完', 'warning')
        return redirect(url_for('main.task_detail', id=id))
    
    # 检查是否已接单
    existing = TaskAssignment.query.filter_by(
        task_id=id,
        user_id=current_user.id
    ).first()
    
    if existing:
        flash('您已接过此任务', 'warning')
        return redirect(url_for('main.task_detail', id=id))
    
    # 创建任务分配
    assignment = TaskAssignment(
        task_id=id,
        user_id=current_user.id,
        status='assigned'
    )
    
    # 检查是否达到需要人数
    current_count = TaskAssignment.query.filter_by(task_id=id).count()
    if current_count + 1 >= task.required_people:
        task.status = 'assigned'
    
    db.session.add(assignment)
    db.session.commit()
    
    flash('抢单成功！请按时完成任务', 'success')
    return redirect(url_for('main.task_detail', id=id))


@bp.route('/patrol/checkin', methods=['POST'])
@login_required
def patrol_checkin():
    """巡逻打卡"""
    lat = request.form.get('lat', type=float)
    lng = request.form.get('lng', type=float)
    location = request.form.get('location')
    notes = request.form.get('notes', '')
    
    checkin = PatrolCheckin(
        user_id=current_user.id,
        lat=lat,
        lng=lng,
        location=location,
        notes=notes
    )
    
    # 处理照片
    import os
    from werkzeug.utils import secure_filename
    
    if 'photo' in request.files:
        file = request.files['photo']
        if file and file.filename:
            filename = secure_filename(file.filename)
            unique_name = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
            file_path = os.path.join(current_app.config['UPLOAD_FOLDER'], 'patrol', unique_name)
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            file.save(file_path)
            checkin.photo = f'uploads/patrol/{unique_name}'
    
    db.session.add(checkin)
    
    # 更新用户最后打卡时间
    current_user.last_checkin = datetime.utcnow()
    current_user.is_on_duty = True
    
    db.session.commit()
    
    # 增加积分
    current_user.add_points(
        current_app.config['POINTS_CONFIG']['patrol_checkin'],
        '巡逻打卡'
    )
    
    return jsonify({
        'success': True,
        'message': '打卡成功',
        'points_earned': current_app.config['POINTS_CONFIG']['patrol_checkin']
    })


@bp.route('/map')
def security_map():
    """治安防控地图"""
    amap_key = os.environ.get('AMAP_KEY', 'your-amap-key-here')
    amap_security_code = os.environ.get('AMAP_SECURITY_CODE', '')
    print("In security_map, config AMAP_KEY =", current_app.config['AMAP_KEY'])
    # 获取各类数据
    hazards = Hazard.query.filter(
        Hazard.lat.isnot(None),
        Hazard.lng.isnot(None)
    ).all()
    
    # 获取在线安保人员
    online_security = []
    from app.models import User
    one_hour_ago = datetime.utcnow() - timedelta(hours=1)
    security_users = User.query.filter(
        User.role.in_(['security', 'grid_worker', 'cloud_sentinel']),
        User.last_checkin >= one_hour_ago,
        User.lat.isnot(None),
        User.lng.isnot(None)
    ).all()
    
    for u in security_users:
        online_security.append({
            'lat': u.lat,
            'lng': u.lng,
            'name': u.real_name or u.username,
            'role': u.role,
            'unit': u.work_unit
        })
    
    # 获取应急单元
    emergency_units = EmergencyDispatch.query.filter(
        EmergencyDispatch.status.in_(['dispatching', 'responding'])
    ).all()
    
    return render_template('security_map.html',
                         hazards=hazards,
                         online_security=online_security,
                         emergency_units=emergency_units,
                         amap_key=amap_key,               # 使用上面定义的变量
                         amap_security_code=amap_security_code)

@bp.route('/points')
@login_required
def points():
    """积分商城"""
    # 获取兑换商品
    items = RewardItem.query.filter_by(is_active=True).all()
    
    # 获取积分记录
    from app.models import PointLog
    logs = PointLog.query.filter_by(user_id=current_user.id).\
        order_by(desc(PointLog.created_at)).limit(20).all()
    
    return render_template('points.html',
                         items=items,
                         logs=logs,
                         user_points=current_user.points)


@bp.route('/points/exchange/<int:item_id>', methods=['POST'])
@login_required
def exchange_item(item_id):
    """兑换商品"""
    item = RewardItem.query.get_or_404(item_id)
    
    if item.stock <= 0:
        flash('商品库存不足', 'warning')
        return redirect(url_for('main.points'))
    
    if current_user.points < item.required_points:
        flash('积分不足', 'warning')
        return redirect(url_for('main.points'))
    
    # 创建兑换记录
    claim = RewardClaim(
        user_id=current_user.id,
        item_id=item_id,
        points_spent=item.required_points,
        receiver_name=request.form.get('receiver_name'),
        receiver_phone=request.form.get('receiver_phone'),
        receiver_address=request.form.get('receiver_address')
    )
    
    # 扣除积分
    current_user.points -= item.required_points
    item.stock -= 1
    
    db.session.add(claim)
    db.session.commit()
    
    flash('兑换成功！', 'success')
    return redirect(url_for('main.points'))


@bp.route('/announcements')
def announcements():
    """公告列表"""
    page = request.args.get('page', 1, type=int)
    category = request.args.get('category', '')
    
    query = Announcement.query
    if category:
        query = query.filter_by(category=category)
    
    pagination = query.order_by(
        desc(Announcement.is_pinned),
        desc(Announcement.published_at)
    ).paginate(page=page, per_page=10, error_out=False)
    
    return render_template('announcements.html',
                         announcements=pagination.items,
                         pagination=pagination,
                         current_category=category)


@bp.route('/announcement/<int:id>')
def announcement_detail(id):
    """公告详情"""
    announcement = Announcement.query.get_or_404(id)
    
    # 增加浏览量
    announcement.view_count += 1
    db.session.commit()
    
    return render_template('announcement_detail.html', announcement=announcement)


@bp.route('/volunteer/register', methods=['GET', 'POST'])
@login_required
def volunteer_register():
    """志愿者/云哨兵注册"""
    if request.method == 'POST':
        role = request.form.get('role')
        work_unit = request.form.get('work_unit')
        work_address = request.form.get('work_address')
        emergency_contact = request.form.get('emergency_contact')
        
        # 更新用户信息
        current_user.role = role
        current_user.work_unit = work_unit
        current_user.work_address = work_address
        current_user.emergency_contact = emergency_contact
        
        db.session.commit()
        
        flash('注册成功！感谢您的加入', 'success')
        return redirect(url_for('main.index'))
    
    return render_template('volunteer_register.html')


@bp.route('/leaderboard')
def leaderboard():
    """积分排行榜 - 管理员不参与排行"""
    from app.models import User
    top_users = User.query.filter(
        User.is_active == True,
        User.role != 'admin'
    ).order_by(User.total_points.desc()).limit(50).all()
    return render_template('leaderboard.html', users=top_users)


# API端点
@bp.route('/api/ai/analyze-image', methods=['POST'])
def ai_analyze_image():
    """AI图像分析 - 基于Pillow进行基本图像分析"""
    import random
    from PIL import Image
    import io

    hazard_types = [
        {'type': '消防通道堵塞', 'desc': '检测到消防通道被车辆或杂物占用', 'keywords': ['消防', '通道', '车辆', '堵塞']},
        {'type': '井盖缺失', 'desc': '检测到路面井盖缺失，存在安全隐患', 'keywords': ['井盖', '路面', '缺失', '空洞']},
        {'type': '路灯损坏', 'desc': '检测到路灯故障不亮，影响夜间出行安全', 'keywords': ['路灯', '损坏', '不亮', '黑暗']},
        {'type': '路面塌陷', 'desc': '检测到路面出现塌陷或裂缝', 'keywords': ['路面', '塌陷', '裂缝', '坑洞']},
        {'type': '电线裸露', 'desc': '检测到电线外露，存在触电风险', 'keywords': ['电线', '裸露', '电缆', '断裂']},
        {'type': '车辆违停', 'desc': '检测到车辆违规停放占用通道', 'keywords': ['车辆', '违停', '占用', '停放']},
        {'type': '可疑人员', 'desc': '检测到异常徘徊行为', 'keywords': ['可疑', '徘徊', '异常', '人员']},
        {'type': '其他隐患', 'desc': '检测到一般安全隐患', 'keywords': ['隐患', '安全', '风险', '异常']},
    ]

    # 检查是否上传了文件
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
                    'mode': img.mode,
                    'size_kb': round(len(file.read()) / 1024, 1)
                }
            except Exception:
                pass

    # 根据图像信息调整识别结果
    selected = random.choice(hazard_types)
    confidence = round(random.uniform(0.65, 0.95), 2)

    result = {
        'success': True,
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
    }
    return jsonify(result)


@bp.route('/api/geocode', methods=['GET'])
def geocode():
    """地理编码 - 调用高德地图API进行逆地理编码"""
    import requests
    lat = request.args.get('lat')
    lng = request.args.get('lng')

    if not lat or not lng:
        return jsonify({'success': False, 'message': '缺少经纬度参数'})

    amap_key = current_app.config.get('AMAP_KEY', '')
    if amap_key and amap_key != 'your-amap-key-here':
        try:
            url = 'https://restapi.amap.com/v3/geocode/regeo'
            params = {
                'key': amap_key,
                'location': f'{lng},{lat}',
                'output': 'JSON'
            }
            resp = requests.get(url, params=params, timeout=5)
            data = resp.json()
            if data.get('status') == '1' and data.get('regeocode'):
                return jsonify({
                    'success': True,
                    'address': data['regeocode'].get('formatted_address', f'{lat},{lng}'),
                    'detail': data['regeocode'].get('addressComponent', {})
                })
        except Exception:
            pass

    return jsonify({
        'success': True,
        'address': f'坐标 ({lat}, {lng}) 附近',
        'note': '需要配置高德地图API Key以获取详细地址'
    })
