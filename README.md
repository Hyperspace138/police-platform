# 群防群治智慧警务平台

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8+-blue.svg" alt="Python 3.8+">
  <img src="https://img.shields.io/badge/Flask-3.0-green.svg" alt="Flask 3.0">
  <img src="https://img.shields.io/badge/Bootstrap-5.3-purple.svg" alt="Bootstrap 5.3">
  <img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT">
</p>

<p align="center">
  <b>警民联动，共建平安社区</b><br>
  人人都是平安合伙人，处处都是防控第一线
</p>

## 项目简介

群防群治智慧警务平台是一个基于 Flask 开发的警民联动平台，旨在整合社会力量，构建"专业+机制+大数据"的新型警务运行模式。平台实现了悬赏令发布、线索举报、安全隐患上报、任务抢单、积分激励等核心功能。

## 核心功能

### 一、悬赏令系统
- 发布悬赏通告（刑事案件、治安案件、寻人启事等）
- 查看悬赏详情和嫌疑人信息
- 在线提交线索举报
- 支持匿名举报，保护举报人隐私

### 二、线索举报系统
- 拍照上传线索
- AI智能识别隐患类型
- GPS自动定位
- 匿名举报与查询码
- 线索处理进度可视化

### 三、安全隐患上报
- 随手拍上传隐患照片
- 隐患类型分类（消防、交通、设施等）
- 紧急程度标记
- 地图可视化展示
- 处理结果反馈

### 四、任务抢单系统
- 发布巡逻、宣传、应急任务
- 在线抢单
- 任务进度跟踪
- 完成审核与积分奖励

### 五、积分激励体系
- 积分获取：提交线索、完成任务、巡逻打卡
- 积分商城兑换礼品
- 积分排行榜
- 荣誉勋章系统

### 六、治安防控地图
- 隐患热力图展示
- 在线安保人员定位
- 应急调度可视化
- 警情高发区域分析

### 七、志愿者管理
- 安保人员注册
- 网格员管理
- 云哨兵招募
- 巡逻打卡系统

## 技术栈

- **后端**: Python 3.8+, Flask 3.0, SQLAlchemy
- **前端**: HTML5, CSS3, JavaScript, Bootstrap 5.3
- **数据库**: SQLite (开发) / MySQL (生产)
- **地图**: 高德地图 API
- **部署**: Gunicorn + Nginx

## 快速开始

本项目使用 SQLite 数据库，无需额外安装数据库软件，开箱即用。

### 1. 克隆项目

```bash
git clone https://github.com/Hyperspace138/police-platform.git
cd police-platform
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 运行应用

```bash
python run.py
```

访问 http://localhost:5000 即可使用。

> **默认管理员账号**：`admin` / `admin123`
>
> 数据库文件 `app.db` 和用户上传的文件已配置在 `.gitignore` 中，不会包含在仓库内。首次运行时会自动创建 SQLite 数据库和管理员账号。
>
> 如需自定义管理员账号或配置高德地图 API Key，可复制 `.env.example` 为 `.env` 后修改对应配置项。不配置地图 Key 不影响基本功能使用。

## 项目结构

```
police-platform/
├── app/                    # 应用主目录
│   ├── __init__.py        # 应用工厂
│   ├── models.py          # 数据库模型
│   ├── routes/            # 路由模块
│   │   ├── main.py        # 主路由
│   │   ├── auth.py        # 认证路由
│   │   ├── api.py         # API路由
│   │   └── admin.py       # 管理后台路由
│   ├── templates/         # HTML模板
│   │   ├── base.html      # 基础模板
│   │   ├── index.html     # 首页
│   │   ├── auth/          # 认证相关模板
│   │   └── admin/         # 管理后台模板
│   ├── static/            # 静态资源
│   │   ├── css/           # 样式文件
│   │   ├── js/            # JavaScript文件
│   │   └── uploads/       # 上传文件
│   └── utils/             # 工具函数
├── config/                # 配置文件
│   └── config.py
├── docs/                  # 文档
│   └── DEPLOY.md          # 部署指南
├── migrations/            # 数据库迁移
├── requirements.txt       # Python依赖
├── run.py                 # 启动脚本
└── README.md              # 项目说明
```

## 功能模块详解

### 用户角色

| 角色 | 说明 | 权限 |
|------|------|------|
| citizen | 普通群众 | 查看悬赏、提交线索、上报隐患 |
| volunteer | 志愿者 | 额外可接任务 |
| security | 安保人员 | 巡逻打卡、应急响应 |
| grid_worker | 网格员 | 社区管理、信息收集 |
| cloud_sentinel | 云哨兵 | 流动人员、见疑即报 |
| police | 民警 | 线索处理、任务审核 |
| admin | 管理员 | 系统管理、用户管理 |

### 积分规则

| 行为 | 积分奖励 |
|------|----------|
| 提交线索 | +10 分 |
| 线索被采纳 | +50 分 |
| 完成任务 | +30 分 |
| 巡逻打卡 | +5 分 |
| 应急响应 | +100 分 |
| 上报隐患 | +10 分 |
| 隐患被解决 | +20 分 |

## API 接口

### 用户相关
- `GET /api/user/info` - 获取用户信息
- `POST /api/user/location` - 更新用户位置
- `POST /api/user/duty` - 切换值班状态

### 悬赏令
- `GET /api/rewards` - 获取悬赏列表
- `GET /api/reward/<id>` - 获取悬赏详情

### 线索
- `POST /api/clues` - 提交线索
- `GET /api/clue/<clue_no>` - 查询线索状态

### 隐患
- `GET /api/hazards` - 获取隐患列表
- `POST /api/hazards` - 上报隐患
- `GET /api/hazards/map` - 获取隐患地图数据

### 任务
- `GET /api/tasks` - 获取任务列表
- `POST /api/task/<id>/claim` - 抢单
- `POST /api/task/<id>/start` - 开始任务
- `POST /api/task/<id>/complete` - 完成任务

### 统计
- `GET /api/stats/dashboard` - 仪表盘统计
- `GET /api/stats/heatmap` - 热力图数据

## 部署指南

详细部署步骤请参考 [docs/DEPLOY.md](docs/DEPLOY.md)

### 快速部署（Ubuntu）

```bash
# 1. 安装依赖
sudo apt update
sudo apt install python3 python3-pip python3-venv nginx -y

# 2. 克隆项目
git clone https://github.com/Hyperspace138/police-platform.git
cd police-platform

# 3. 安装 Python 依赖
pip install -r requirements.txt

# 4. （可选）配置环境变量
cp .env.example .env
nano .env  # 修改高德地图 Key 等配置

# 5. 启动服务
python run.py
```

访问 http://your-server-ip:5000 即可使用，默认管理员账号 admin / admin123。

生产环境建议使用 Gunicorn + Nginx，详见 [docs/DEPLOY.md](docs/DEPLOY.md)。

## 配置说明

### 高德地图 API Key

1. 访问 [高德地图开放平台](https://lbs.amap.com/)
2. 注册账号并创建应用
3. 申请 Web 端 JS API Key
4. 将 Key 填入 `.env` 文件的 `AMAP_KEY`

### 数据库配置

**SQLite（开发环境）:**
```env
DATABASE_URL=sqlite:///app.db
```

**MySQL（生产环境）:**
```env
DATABASE_URL=mysql+pymysql://username:password@localhost/police_platform
```

## 开发计划

- [x] 基础框架搭建
- [x] 用户认证系统
- [x] 悬赏令系统
- [x] 线索举报系统
- [x] 隐患上报系统
- [x] 任务抢单系统
- [x] 积分商城
- [x] 治安防控地图
- [ ] 消息推送系统
- [ ] 数据统计报表
- [ ] 小程序端
- [ ] AI智能识别升级

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本项目
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开一个 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

## 致谢

- [Flask](https://flask.palletsprojects.com/)
- [Bootstrap](https://getbootstrap.com/)
- [高德地图](https://lbs.amap.com/)

## 联系方式

如有问题或建议，欢迎联系我们：

- 邮箱: support@police-platform.com
- 电话: 110

---

<p align="center">
  <sub>Built with ❤️ for a safer community</sub>
</p>
