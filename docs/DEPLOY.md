# 群防群治智慧警务平台 - 部署指南

## 系统要求

- Python 3.8+
- 内存：至少 1GB
- 硬盘：至少 5GB 可用空间
- 操作系统：Linux (Ubuntu/CentOS) 或 Windows Server

## 一、环境准备

### 1.1 安装 Python 3.8+

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3 python3-pip python3-venv -y
```

**CentOS/RHEL:**
```bash
sudo yum install python3 python3-pip -y
```

### 1.2 安装 Nginx（生产环境推荐）

**Ubuntu/Debian:**
```bash
sudo apt install nginx -y
```

**CentOS/RHEL:**
```bash
sudo yum install nginx -y
```

## 二、项目部署

### 2.1 上传项目到服务器

将项目文件上传到服务器，例如 `/var/www/police-platform` 目录：

```bash
# 创建目录
sudo mkdir -p /var/www/police-platform
cd /var/www/police-platform

# 上传项目文件（使用 scp 或 ftp）
# scp -r /local/path/police-platform/* user@server:/var/www/police-platform/
```

### 2.2 创建虚拟环境

```bash
cd /var/www/police-platform
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
```

### 2.3 安装依赖

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 2.4 配置环境变量

```bash
# 复制环境变量示例文件
cp .env.example .env

# 编辑 .env 文件
nano .env
```

修改以下配置：

```env
FLASK_ENV=production
SECRET_KEY=your-random-secret-key-here  # 必须修改为随机字符串
DATABASE_URL=sqlite:///app.db  # 或使用 MySQL: mysql+pymysql://user:pass@localhost/police_platform
AMAP_KEY=your-amap-key-here  # 高德地图API Key
```

### 2.5 初始化数据库

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

### 2.6 测试运行

```bash
python run.py
```

访问 `http://your-server-ip:5000` 测试是否正常。

## 三、生产环境配置

### 3.1 使用 Gunicorn

安装 Gunicorn：
```bash
pip install gunicorn
```

创建 Gunicorn 配置文件 `gunicorn.conf.py`：

```python
import multiprocessing

bind = "0.0.0.0:8000"
workers = multiprocessing.cpu_count() * 2 + 1
worker_class = "sync"
worker_connections = 1000
timeout = 120
keepalive = 2
errorlog = "/var/log/gunicorn/error.log"
accesslog = "/var/log/gunicorn/access.log"
pidfile = "/var/run/gunicorn.pid"
daemon = True
```

创建日志目录：
```bash
sudo mkdir -p /var/log/gunicorn
sudo mkdir -p /var/run/gunicorn
```

启动 Gunicorn：
```bash
gunicorn -c gunicorn.conf.py run:app
```

### 3.2 配置 Systemd 服务

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

### 3.3 配置 Nginx

创建 Nginx 配置文件 `/etc/nginx/sites-available/police-platform`：

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 修改为您的域名

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

### 3.4 配置 HTTPS（推荐）

使用 Certbot 免费 SSL 证书：

```bash
# 安装 Certbot
sudo apt install certbot python3-certbot-nginx -y

# 获取证书
sudo certbot --nginx -d your-domain.com

# 自动续期
sudo systemctl enable certbot.timer
```

## 四、常见问题

### 4.1 权限问题

```bash
# 修改项目目录权限
sudo chown -R www-data:www-data /var/www/police-platform
sudo chmod -R 755 /var/www/police-platform

# 确保上传目录可写
sudo chmod -R 775 /var/www/police-platform/app/static/uploads
```

### 4.2 数据库迁移失败

```bash
# 删除迁移目录重新初始化
rm -rf migrations
flask db init
flask db migrate
flask db upgrade
```

### 4.3 日志查看

```bash
# Gunicorn 日志
sudo tail -f /var/log/gunicorn/error.log
sudo tail -f /var/log/gunicorn/access.log

# Nginx 日志
sudo tail -f /var/log/nginx/error.log
sudo tail -f /var/log/nginx/access.log

# Systemd 日志
sudo journalctl -u police-platform -f
```

## 五、更新部署

```bash
cd /var/www/police-platform

# 拉取最新代码
git pull

# 激活虚拟环境
source venv/bin/activate

# 安装新依赖
pip install -r requirements.txt

# 执行数据库迁移
flask db migrate
flask db upgrade

# 重启服务
sudo systemctl restart police-platform
```

## 六、备份与恢复

### 6.1 备份数据库

```bash
# SQLite 备份
cp /var/www/police-platform/app.db /backup/police-platform-$(date +%Y%m%d).db

# MySQL 备份
mysqldump -u root -p police_platform > /backup/police-platform-$(date +%Y%m%d).sql
```

### 6.2 备份上传文件

```bash
tar -czf /backup/uploads-$(date +%Y%m%d).tar.gz /var/www/police-platform/app/static/uploads
```

### 6.3 恢复数据

```bash
# 恢复数据库
cp /backup/police-platform-20240101.db /var/www/police-platform/app.db

# 恢复上传文件
tar -xzf /backup/uploads-20240101.tar.gz -C /
```

## 七、安全建议

1. **修改默认密码**：首次登录后立即修改管理员密码
2. **使用强密钥**：生产环境必须使用随机生成的 SECRET_KEY
3. **定期更新**：及时更新系统和依赖包的安全补丁
4. **防火墙配置**：只开放必要的端口（80, 443）
5. **定期备份**：设置自动备份任务

## 八、联系方式

如有问题，请联系技术支持。
