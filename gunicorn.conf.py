import multiprocessing

# 绑定地址和端口
bind = "0.0.0.0:8000"          # 只监听本地，由 Nginx 转发

# 工作进程数：CPU核心数 * 2 + 1
workers = multiprocessing.cpu_count() * 2 + 1

# 工作模式（同步）
worker_class = "sync"

# 每个工作进程的最大并发连接数
worker_connections = 1000

# 超时设置（秒）
timeout = 120

# 保持连接时间
keepalive = 2

# 日志文件
errorlog = "/var/log/gunicorn/error.log"
accesslog = "/var/log/gunicorn/access.log"

# PID 文件
pidfile = "/tmp/gunicorn.pid"

# 守护进程模式（后台运行）
daemon = False
preload_app = True
