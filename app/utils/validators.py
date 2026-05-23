# -*- coding: utf-8 -*-
"""统一验证工具"""
import re
import os
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
ALLOWED_MIMETYPES = {'image/png', 'image/jpeg', 'image/gif', 'image/webp'}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB


def validate_phone(phone):
    """验证中国大陆手机号格式"""
    if not phone or not phone.strip():
        return False, '请输入手机号'
    phone = phone.strip()
    if not re.match(r'^1[3-9]\d{9}$', phone):
        return False, '请输入正确的11位手机号码'
    return True, ''


def validate_username(username):
    """验证用户名格式"""
    if not username or not username.strip():
        return False, '请输入用户名'
    username = username.strip()
    if len(username) < 2:
        return False, '用户名至少2个字符'
    if len(username) > 20:
        return False, '用户名最多20个字符'
    if not re.match(r'^[\w一-鿿]+$', username):
        return False, '用户名只能包含中文、字母、数字和下划线'
    return True, ''


def validate_password(password):
    """验证密码强度"""
    if not password:
        return False, '请输入密码'
    if len(password) < 8:
        return False, '密码长度至少为8位'
    if not re.search(r'[A-Za-z]', password):
        return False, '密码必须包含字母'
    if not re.search(r'\d', password):
        return False, '密码必须包含数字'
    return True, ''


def validate_email(email):
    """验证邮箱格式（可选字段）"""
    if not email or not email.strip():
        return True, ''
    if not re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', email):
        return False, '请输入正确的邮箱地址'
    return True, ''


def validate_id_card(id_card):
    """验证中国18位身份证号格式"""
    if not id_card or len(id_card) != 18:
        return False, '身份证号必须为18位'
    # 前17位必须是数字
    if not id_card[:17].isdigit():
        return False, '身份证号格式不正确'
    # 校验位验证
    weights = [7, 9, 10, 5, 8, 4, 2, 1, 6, 3, 7, 9, 10, 5, 8, 4, 2]
    check_codes = '10X98765432'
    total = sum(int(id_card[i]) * weights[i] for i in range(17))
    if check_codes[total % 11] != id_card[17].upper():
        return False, '身份证号校验不通过'
    return True, ''


def validate_uploaded_file(file, check_content=True):
    """统一文件上传验证
    返回 (is_valid, error_message, safe_filename)
    """
    if not file or not file.filename:
        return False, '未选择文件', None

    filename = secure_filename(file.filename)
    if not filename:
        return False, '文件名无效', None

    ext = filename.rsplit('.', 1)[-1].lower() if '.' in filename else ''
    if ext not in ALLOWED_EXTENSIONS:
        return False, f'不支持的文件类型: .{ext}，仅支持图片格式', None

    if check_content:
        # 检查文件大小
        file.seek(0, os.SEEK_END)
        size = file.tell()
        file.seek(0)
        if size > MAX_FILE_SIZE:
            return False, f'文件大小不能超过{MAX_FILE_SIZE // 1024 // 1024}MB', None

        # 检查MIME类型
        if file.mimetype and file.mimetype not in ALLOWED_MIMETYPES:
            return False, '文件内容类型不合法', None

    return True, '', filename
