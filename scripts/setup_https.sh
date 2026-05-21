#!/bin/bash
# 群防群治智慧警务平台 - HTTPS自动配置脚本
# 使用方法: sudo bash setup_https.sh your-domain.com

set -e

DOMAIN="${1}"
if [ -z "$DOMAIN" ]; then
    echo "用法: sudo bash setup_https.sh <你的域名>"
    echo "例如: sudo bash setup_https.sh police.example.com"
    exit 1
fi

echo "========================================"
echo "  群防群治智慧警务平台 - HTTPS配置"
echo "  域名: $DOMAIN"
echo "========================================"
echo ""

# 检查是否以root运行
if [ "$EUID" -ne 0 ]; then
    echo "请使用 sudo 运行此脚本"
    exit 1
fi

# 1. 安装 Nginx（如未安装）
echo "[1/5] 检查 Nginx..."
if ! command -v nginx &> /dev/null; then
    apt update && apt install nginx -y
    echo "Nginx 安装完成"
else
    echo "Nginx 已安装"
fi

# 2. 安装 Certbot
echo "[2/5] 安装 Certbot..."
if ! command -v certbot &> /dev/null; then
    apt install certbot python3-certbot-nginx -y
    echo "Certbot 安装完成"
else
    echo "Certbot 已安装"
fi

# 3. 创建 Nginx 配置
echo "[3/5] 配置 Nginx..."
NGINX_CONF="/etc/nginx/sites-available/police-platform"
cat > "$NGINX_CONF" << NGINXEOF
server {
    listen 80;
    server_name $DOMAIN;
    return 301 https://\$host\$request_uri;
}

server {
    listen 443 ssl http2;
    server_name $DOMAIN;

    # SSL 证书（Certbot 会自动填充）
    ssl_certificate /etc/letsencrypt/live/$DOMAIN/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/$DOMAIN/privkey.pem;

    # SSL 安全配置
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256;
    ssl_prefer_server_ciphers off;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;

    # 安全头
    add_header Strict-Transport-Security "max-age=63072000" always;
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header X-XSS-Protection "1; mode=block" always;

    # 日志
    access_log /var/log/nginx/police-platform-access.log;
    error_log /var/log/nginx/police-platform-error.log;

    # 上传大小限制
    client_max_body_size 16M;

    # 静态文件
    location /static {
        alias /var/www/police-platform/app/static;
        expires 30d;
        add_header Cache-Control "public, immutable";
    }

    location /uploads {
        alias /var/www/police-platform/app/static/uploads;
    }

    # 代理到 Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_set_header X-Forwarded-Host \$host;
        proxy_set_header X-Forwarded-Port \$server_port;
        proxy_connect_timeout 120s;
        proxy_read_timeout 120s;
    }
}
NGINXEOF

# 启用站点
ln -sf "$NGINX_CONF" /etc/nginx/sites-enabled/police-platform
rm -f /etc/nginx/sites-enabled/default

# 测试配置
nginx -t

# 4. 获取 SSL 证书
echo "[4/5] 获取 SSL 证书..."
certbot --nginx -d "$DOMAIN" --non-interactive --agree-tos --email admin@"$DOMAIN" --redirect

# 5. 重启服务
echo "[5/5] 重启服务..."
systemctl restart nginx

# 设置证书自动续期
systemctl enable certbot.timer

echo ""
echo "========================================"
echo "  HTTPS 配置完成！"
echo "  访问地址: https://$DOMAIN"
echo "========================================"
echo ""
echo "证书将在到期前自动续期（certbot.timer）"
echo "如需手动续期: sudo certbot renew"
