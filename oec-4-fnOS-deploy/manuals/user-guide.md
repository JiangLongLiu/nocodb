# NocoDB 用户操作手册

## 访问地址

| 服务 | 地址 | 说明 |
|------|------|------|
| NocoDB | http://100.110.75.2:8088 | 主要工作界面（需 Tailscale 连接） |
| MinIO Console | http://100.110.75.2:9001 | 对象存储管理界面 |

> **前提条件**：访问设备需安装并登录 Tailscale，确保在同一个 Tailnet 中。

---

## 首次使用

### 1. 注册管理员账户

1. 打开浏览器访问 http://100.110.75.2:8088
2. 系统会自动跳转到注册页面（Sign Up）
3. 填写 E-mail 和密码（密码建议 8 位以上，含大小写字母和数字）
4. 点击 **SIGN UP** 完成注册
5. 注册成功后自动登录到 NocoDB 主界面

### 2. 配置 MinIO 存储（用于附件上传/下载）

注册完成后，建议配置 MinIO 作为附件存储后端：

1. 创建一个项目（Project），或使用默认项目
2. 进入项目后，点击左下角 **Project Settings**（项目设置）
3. 选择 **Data Sources** 或 **Plugins**（取决于 NocoDB 版本）
4. 找到 **Storage** > **Minio** 插件，点击 **Install/Configure**
5. 填写以下配置：

| 配置项 | 值 |
|--------|-----|
| Minio Endpoint | `100.110.75.2` |
| Port | `9000` |
| Bucket Name | `nocodb-attachments` |
| Access Key | 查看 .env 文件中的 `MINIO_ROOT_USER` |
| Access Secret | 查看 .env 文件中的 `MINIO_ROOT_PASSWORD` |
| Use SSL | 关闭（unchecked） |

6. 点击 **Test** 测试连接，确认显示 "Connection successful"
7. 点击 **Save** 保存配置

> 配置完成后，所有表格中的附件字段将自动存储到 MinIO，并通过 Tailscale 地址提供上传/下载。

---

## 日常操作

### 创建数据表

1. 在项目主界面点击 **+** 按钮
2. 选择 **Create Table**（创建表格）
3. 输入表名，点击确认
4. 通过列标题旁的 **+** 添加字段

### 添加附件字段

1. 在表格中点击 **+** 添加新列
2. 字段类型选择 **Attachment**
3. 输入字段名称（如 "文件"、"图片" 等）
4. 保存后即可在该字段上传文件

### 上传/下载附件

- **上传**：点击附件字段单元格，拖拽文件到上传区域或点击浏览选择文件
- **下载**：点击已上传的文件名即可下载
- **预览**：图片和 PDF 文件支持在线预览

---

## 运维操作

### 使用部署脚本管理容器

部署脚本位于 `scripts/deploy.py`，支持以下操作：

```bash
# 查看容器状态
python scripts/deploy.py --action status

# 查看 NocoDB 日志
python scripts/deploy.py --action logs --service nocodb --lines 100

# 查看 MinIO 日志
python scripts/deploy.py --action logs --service minio --lines 50

# 停止所有服务
python scripts/deploy.py --action stop

# 启动所有服务
python scripts/deploy.py --action start

# 重启所有服务
python scripts/deploy.py --action restart

# 上传配置并完整部署
python scripts/deploy.py --action full
```

### 直接 SSH 管理

如需直接操作远程主机：

```bash
# SSH 登录
ssh root@192.168.1.54

# 查看容器状态
cd /vol1/docker/mycontainers/nocodb
docker compose ps

# 查看所有日志
docker compose logs -f

# 重启单个服务
docker compose restart nocodb
```

### 数据备份

所有数据存储在远程主机 `/vol1/docker/mycontainers/nocodb/` 目录下：

| 目录 | 内容 |
|------|------|
| `nocodb_data/` | NocoDB 应用数据 |
| `postgres_data/` | PostgreSQL 数据库文件 |
| `redis_data/` | Redis 缓存数据 |
| `minio_data/` | MinIO 附件存储 |
| `docker-compose.yml` | 容器编排配置 |
| `.env` | 环境变量（含密码等敏感信息） |

**备份方法**：停止服务后，将上述目录整体备份即可。

```bash
cd /vol1/docker/mycontainers/nocodb
docker compose down
tar -czf nocodb-backup-$(date +%Y%m%d).tar.gz .
docker compose up -d
```

---

## 常见问题

### Q: 无法访问 NocoDB
**A**: 检查 Tailscale 是否已连接，尝试 `ping 100.110.75.2` 确认网络连通。

### Q: 附件上传失败
**A**: 确认已配置 MinIO 插件（见"配置 MinIO 存储"章节），检查 MinIO 服务是否正常运行。

### Q: 容器启动失败
**A**: 运行 `python scripts/deploy.py --action logs` 查看日志，常见原因：
- 端口被占用：运行端口检测脚本确认端口可用性
- 镜像拉取失败：配置 Docker 代理后重试

### Q: 数据库连接失败
**A**: 检查 PostgreSQL 容器是否健康：`docker compose ps`，确认 db 服务状态为 healthy。

---

## 安全注意事项

1. `.env` 文件包含数据库密码和 MinIO 密钥，请妥善保管
2. 定期更换密码，更新后需重新上传配置并重启服务
3. 生产环境建议启用 HTTPS（通过反向代理实现）
