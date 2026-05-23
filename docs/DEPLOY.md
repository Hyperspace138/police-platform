# 群防群治智慧警务平台 - GitHub 部署指南

## 系统要求

- Python 3.8+
- 内存：至少 1GB
- 硬盘：至少 5GB 可用空间
- 操作系统：Linux (Ubuntu/CentOS) 或 Windows Server
- Git

## 一、从 GitHub 克隆项目

```bash
# 克隆仓库
cd /var/www
git clone https://github.com/Hyperspace138/police-platform.git
cd police-platform
```

如果使用 SSH 方式：

```bash
git clone git@github.com:Hyperspace138/police-platform.git
```

## 二、环境准备

### 2.1 安装 Python 3.8+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

**CentOS/RHEL:**
```bash
sudo yum install python3 python3-pip -y
```

### 2.2 安装 Nginx（生产环境推荐）

**Ubuntu/Debian:**
```bash
sudo apt install nginx -y
```

**CentOS/RHEL:**
```bash
sudo yum install nginx -y
```

### 2.3 创建虚拟环境

```bash
cd /var/www/police-platform
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2.4 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

## 三、配置项目

### 3.1 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件
nano .env
```

修改以下配置：

```env
FLASK_ENV=production
SECRET_KEY=<生成随机密钥>
DATABASE_URL=sqlite:///app.db
AMAP_KEY=<你的高德地图API Key>
ADMIN_USERNAME=admin
ADMIN_PASSWORD=<修改默认密码>
ADMIN_PHONE=13800138000
```

生成随机密钥：

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3.2 初始化数据库

```bash
# 设置环境变量
export FLASK_APP=run.py

# 初始化数据库
flask db init
flask db migrate -m "Initial migration"
flask db upgrade

# 创建管理员账号
flask deploy
```

### 3.3 测试运行

```bash
python run.py
```

访问 `http://your-server-ip:5000` 测试是否正常。

## 四、生产环境配置

### 4.1 使用 Gunicorn

安装 Gunicorn：

```bash
pip install gunicorn
```

创建日志目录：

```bash
sudo mkdir -p /var/log/gunicorn
```

项目已包含 `gunicorn.conf.py`，直接使用：

```bash
gunicorn -c gunicorn.conf.py run:app
```

### 4.2 配置 Systemd 服务

创建服务文件 `/etc/systemd/system/police-platform.service`：

```ini
[Unit]
Description=Police Platform Gunicorn Service
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/police-platform
Environment="PATH=/var/www/police-platform/venv/bin"
Environment="FLASK_ENV=production"
ExecStart=/var/www/police-platform/venv/bin/gunicorn -c gunicorn.conf.py run:app
ExecReload=/bin/kill -s HUP $MAINPID
KillMode=mixed
TimeoutStopSec=5
PrivateTmp=true

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl start police-platform
sudo systemctl enable police-platform
```

### 4.3 配置 Nginx

创建 Nginx 配置文件 `/etc/nginx/sites-available/police-platform`：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 修改为你的域名或 IP

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /var/www/police-platform/app/static;
        expires 30d;
    }

    location /uploads {
        alias /var/www/police-platform/app/static/uploads;
        expires 30d;
    }

    client_max_body_size 16M;
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/police-platform /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 4.4 配置 HTTPS（推荐）

使用 Certbot 免费 SSL 证书：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo systemctl enable certbot.timer
```

## 五、权限配置

```bash
# 修改项目目录权限
sudo chown -R www-data:www-data /var/www/police-platform
sudo chmod -R 755 /var/www/police-platform

# 确保上传目录可写
sudo chmod -R 775 /var/www/police-platform/app/static/uploads
```

## 六、通过 GitHub 更新部署

每次推送代码到 GitHub 仓库后，在服务器上执行：

```bash
cd /var/www/police-platform

# 拉取最新代码
git pull origin main

# 激活虚拟环境
source venv/bin/activate

# 安装新依赖（如有新增）
pip install -r requirements.txt

# 执行数据库迁移（如有模型变更）
flask db migrate -m "描述变更内容"
flask db upgrade

# 恢复上传目录权限
sudo chmod -R 775 /var/www/police-platform/app/static/uploads

# 重启服务
sudo systemctl restart police-platform
```

一键更新脚本（保存为 `/var/www/police-platform/update.sh`）：

```bash
#!/bin/bash
set -e
cd /var/www/police-platform
echo ">>> 拉取最新代码..."
git pull origin main
echo ">>> 安装依赖..."
source venv/bin/activate
pip install -r requirements.txt
echo ">>> 数据库迁移..."
flask db migrate -m "update $(date +%Y%m%d)"
flask db upgrade
echo ">>> 修复权限..."
sudo chmod -R 775 /var/www/police-platform/app/static/uploads
echo ">>> 重启服务..."
sudo systemctl restart police-platform
echo ">>> 更新完成！"
```

```bash
chmod +x /var/www/police-platform/update.sh
```

## 七、备份与恢复

### 7.1 备份数据库

```bash
cp /var/www/police-platform/app.db /backup/police-platform-$(date +%Y%m%d).db
```

### 7.2 备份上传文件

```bash
tar -czf /backup/uploads-$(date +%Y%m%d).tar.gz /var/www/police-platform/app/static/uploads
```

### 7.3 恢复数据

```bash
cp /backup/police-platform-20240101.db /var/www/police-platform/app.db
tar -xzf /backup/uploads-20240101.tar.gz -C /
sudo systemctl restart police-platform
```

## 八、日志查看

```bash
# Gunicorn 日志
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/gunicorn/access.log

# Nginx 日志
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Systemd 服务日志
sudo journalctl -u police-platform -f
```

## 九、常见问题

### 数据库迁移失败

```bash
rm -rf migrations
flask db init
flask db migrate
flask db upgrade
```

### Git pull 冲突

```bash
git stash
git pull origin main
git stash pop
```

### 端口被占用

```bash
sudo lsof -i :8000
sudo kill -9 <PID>
sudo systemctl restart police-platform
```

## 十、安全建议

1. **不要提交 .env 文件**：`.gitignore` 已排除 .env，确保敏感信息不会上传到 GitHub
2. **修改默认密码**：首次部署后立即修改管理员密码
3. **使用强密钥**：生产环境必须使用随机生成的 SECRET_KEY
4. **定期更新**：`git pull` 拉取最新安全补丁
5. **防火墙配置**：只开放必要的端口（80, 443）
6. **定期备份**：设置 crontab 自动备份任务

## 服务器信息

- **IP**: 101.201.29.99
- **GitHub**: https://github.com/Hyperspace138/police-platform
- **部署路径**: /var/www/police-platform
- **服务名**: police-platform.service
