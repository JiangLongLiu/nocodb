# NocoDB oec-4-fnOS 部署项目

在 oec-4-fnOS 主机（RK3566-OECT-4）上部署 NocoDB 低代码平台，通过 Tailscale 网络安全访问。

## 部署概览

| 项目 | 值 |
|------|-----|
| 目标主机 | 192.168.1.54 (RK3566-OECT-4-fnOS) |
| Tailscale 地址 | 100.110.75.2 |
| NocoDB 访问 | http://100.110.75.2:8088 |
| MinIO Console | http://100.110.75.2:9001 |
| 远程工作目录 | /vol1/docker/mycontainers/nocodb |
| Git 分支 | oec-4-fnOS-deploy |

## 服务架构

```
NocoDB (8088) + Worker + PostgreSQL + Redis + MinIO (9000/9001)
```

- **NocoDB**: 低代码数据库平台主服务
- **Worker**: NocoDB 后台工作进程
- **PostgreSQL 17**: 主数据库
- **Redis 7**: 缓存和会话管理
- **MinIO**: S3 兼容对象存储，用于附件管理

## 文档索引

| 文档 | 路径 | 说明 |
|------|------|------|
| 用户操作手册 | [manuals/user-guide.md](manuals/user-guide.md) | 首次使用、MinIO 配置、日常操作、运维管理 |
| 部署进度跟踪 | [docs/progress.md](docs/progress.md) | 任务进度、端口分配、错误记录 |
| Docker 编排配置 | [configs/docker-compose.yml](configs/docker-compose.yml) | 容器服务编排文件 |
| 环境变量配置 | [configs/.env](configs/.env) | 脱敏环境变量（含密码等敏感信息） |
| 部署脚本 | [scripts/deploy.py](scripts/deploy.py) | 无人值守部署/管理脚本 |
| 主机凭证 | [password.csv](password.csv) | SSH 连接凭证（敏感文件） |

## 快速开始

### 前提条件

- 访问设备安装 Tailscale 并加入同一 Tailnet
- 本地安装 Python 3.x + paramiko + scp 库

### 首次访问

1. 打开 http://100.110.75.2:8088 注册管理员账户
2. 按 [用户操作手册](manuals/user-guide.md) 配置 MinIO 存储插件
3. 开始创建数据表和附件字段

### 重新部署 / 配置更新

```bash
# 完整部署（上传配置 + 拉取镜像 + 启动服务）
python scripts/deploy.py --action full

# 仅上传配置（不重启服务）
python scripts/deploy.py --action upload

# 重启服务
python scripts/deploy.py --action restart

# 查看状态
python scripts/deploy.py --action status
```

## 端口分配

| 服务 | 端口 | 外部暴露 |
|------|------|----------|
| NocoDB | 8088 | 是 |
| MinIO API | 9000 | 是 |
| MinIO Console | 9001 | 是 |
| PostgreSQL | 5433 | 否（仅 Docker 内部） |
| Redis | 6379 | 否（仅 Docker 内部） |

## 敏感文件说明

以下文件包含敏感信息，仅推送到 Gitea 私有仓库，不推送到 GitHub 公开仓库：

- `password.csv` - SSH 凭证
- `configs/.env` - 数据库密码、MinIO 密钥
