# -*- coding: utf-8 -*-
"""
群防群治智慧警务平台 - 模板过滤器
"""
import json
from datetime import datetime


def register_filters(app):
    """注册所有模板过滤器"""
    
    @app.template_filter('fromjson')
    def fromjson(value):
        """将JSON字符串转换为Python对象"""
        if not value:
            return []
        try:
            return json.loads(value)
        except:
            return []
    
    @app.template_filter('tojson')
    def tojson_filter(value):
        """将Python对象转换为JSON字符串"""
        return json.dumps(value, ensure_ascii=False)
    
    @app.template_filter('format_datetime')
    def format_datetime(value, format='%Y-%m-%d %H:%M'):
        """格式化日期时间"""
        if value is None:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except:
                return value
        return value.strftime(format)
    
    @app.template_filter('timeago')
    def timeago(value):
        """显示相对时间"""
        if value is None:
            return ''
        
        now = datetime.now()
        if isinstance(value, str):
            try:
                value = datetime.strptime(value, '%Y-%m-%d %H:%M:%S')
            except:
                return value
        
        diff = now - value
        
        if diff.days > 365:
            return f'{diff.days // 365}年前'
        elif diff.days > 30:
            return f'{diff.days // 30}个月前'
        elif diff.days > 0:
            return f'{diff.days}天前'
        elif diff.seconds > 3600:
            return f'{diff.seconds // 3600}小时前'
        elif diff.seconds > 60:
            return f'{diff.seconds // 60}分钟前'
        else:
            return '刚刚'
    
    @app.template_filter('truncate')
    def truncate_filter(value, length=100, suffix='...'):
        """截断文本"""
        if not value:
            return ''
        if len(value) <= length:
            return value
        return value[:length] + suffix
