#!/usr/bin/env python3
"""
NocoDB oec-4-fnOS 无人值守部署脚本
用法: python deploy.py [--csv <path>] [--action <upload|start|stop|restart|status|logs|full>]
"""

import argparse
import csv
import os
import sys
import time
import paramiko
from scp import SCPClient

# ============================================================
# 默认配置
# ============================================================
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DEPLOY_DIR = os.path.dirname(SCRIPT_DIR)
DEFAULT_CSV = os.path.join(DEPLOY_DIR, "password.csv")
CONFIGS_DIR = os.path.join(DEPLOY_DIR, "configs")
REMOTE_BASE_DIR = "/vol1/docker/mycontainers/nocodb"
COMPOSE_TIMEOUT = 300  # docker compose 操作超时(秒)


def load_credentials(csv_path):
    """从 CSV 文件读取主机凭证"""
    if not os.path.exists(csv_path):
        print(f"[ERROR] 凭证文件不存在: {csv_path}")
        sys.exit(1)

    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        hosts = []
        for row in reader:
            ip = row.get("IP地址") or row.get("host") or row.get("ip")
            user = row.get("用户名") or row.get("username") or row.get("user")
            pwd = row.get("密码") or row.get("password") or row.get("pass")
            port = int(row.get("SSH端口") or row.get("port") or row.get("ssh_port") or 22)
            if ip and user and pwd:
                hosts.append({"host": ip, "user": user, "password": pwd, "port": port})
    if not hosts:
        print("[ERROR] CSV 中未找到有效凭证")
        sys.exit(1)
    return hosts


def create_ssh_client(host_info):
    """创建 SSH 连接"""
    print(f"[INFO] 连接 {host_info['host']}:{host_info['port']} ...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    ssh.connect(
        hostname=host_info["host"],
        port=host_info["port"],
        username=host_info["user"],
        password=host_info["password"],
        timeout=30,
    )
    print(f"[OK] SSH 连接成功: {host_info['user']}@{host_info['host']}")
    return ssh


def exec_remote(ssh, cmd, timeout=120, show_output=True):
    """执行远程命令并返回输出"""
    print(f"[CMD] {cmd}")
    stdin, stdout, stderr = ssh.exec_command(cmd, timeout=timeout)
    out = stdout.read().decode("utf-8", errors="replace").strip()
    err = stderr.read().decode("utf-8", errors="replace").strip()
    exit_code = stdout.channel.recv_exit_status()
    if show_output:
        if out:
            for line in out.splitlines():
                print(f"  [OUT] {line}")
        if err:
            for line in err.splitlines():
                print(f"  [ERR] {line}")
    print(f"  [EXIT] {exit_code}")
    return out, err, exit_code


def upload_configs(ssh, host_info):
    """SCP 上传配置文件到远程主机"""
    print(f"\n{'='*60}")
    print(f"上传配置文件到 {host_info['host']}")
    print(f"{'='*60}")

    # 确保远程目录存在
    exec_remote(ssh, f"mkdir -p {REMOTE_BASE_DIR}")

    # 上传文件列表
    files_to_upload = []
    for fname in os.listdir(CONFIGS_DIR):
        fpath = os.path.join(CONFIGS_DIR, fname)
        if os.path.isfile(fpath):
            files_to_upload.append((fpath, f"{REMOTE_BASE_DIR}/{fname}"))

    if not files_to_upload:
        print("[WARN] configs/ 目录下没有文件可上传")
        return

    with SCPClient(ssh.get_transport()) as scp:
        for local_path, remote_path in files_to_upload:
            print(f"[SCP] {os.path.basename(local_path)} -> {remote_path}")
            scp.put(local_path, remote_path)

    print(f"[OK] {len(files_to_upload)} 个文件上传完成")

    # 验证上传
    out, _, _ = exec_remote(ssh, f"ls -la {REMOTE_BASE_DIR}/")
    print("[OK] 远程目录内容:")


def start_services(ssh, host_info):
    """启动容器服务"""
    print(f"\n{'='*60}")
    print(f"启动服务 on {host_info['host']}")
    print(f"{'='*60}")

    # 拉取镜像
    print("\n[STEP 1] 拉取 Docker 镜像 ...")
    out, err, code = exec_remote(
        ssh,
        f"cd {REMOTE_BASE_DIR} && docker compose pull",
        timeout=COMPOSE_TIMEOUT,
    )
    if code != 0:
        print("[ERROR] 镜像拉取失败，尝试继续启动...")

    # 启动服务
    print("\n[STEP 2] 启动容器 ...")
    out, err, code = exec_remote(
        ssh,
        f"cd {REMOTE_BASE_DIR} && docker compose up -d",
        timeout=COMPOSE_TIMEOUT,
    )
    if code != 0:
        print("[ERROR] 容器启动失败!")
        return False

    print("[OK] 容器启动命令已执行")

    # 等待健康检查
    print("\n[STEP 3] 等待服务就绪 ...")
    for i in range(20):
        time.sleep(10)
        out, _, _ = exec_remote(
            ssh,
            f"cd {REMOTE_BASE_DIR} && docker compose ps --format json 2>/dev/null || docker compose ps",
            timeout=30,
            show_output=False,
        )
        # 检查 NocoDB 健康状态
        health_out, _, health_code = exec_remote(
            ssh,
            "curl -sf http://localhost:8088/api/v1/health 2>/dev/null || echo 'UNHEALTHY'",
            timeout=10,
            show_output=False,
        )
        if "UNHEALTHY" not in health_out and health_out.strip():
            print(f"[OK] NocoDB 服务已就绪! (第 {(i+1)*10} 秒)")
            exec_remote(
                ssh,
                f"cd {REMOTE_BASE_DIR} && docker compose ps",
                show_output=True,
            )
            return True
        print(f"  等待中... ({(i+1)*10}s)")

    print("[WARN] 健康检查超时，请手动检查容器状态")
    return False


def stop_services(ssh, host_info):
    """停止容器服务"""
    print(f"\n{'='*60}")
    print(f"停止服务 on {host_info['host']}")
    print(f"{'='*60}")
    exec_remote(
        ssh,
        f"cd {REMOTE_BASE_DIR} && docker compose down",
        timeout=120,
    )
    print("[OK] 服务已停止")


def show_status(ssh, host_info):
    """显示容器状态"""
    print(f"\n{'='*60}")
    print(f"容器状态 on {host_info['host']}")
    print(f"{'='*60}")
    exec_remote(ssh, f"cd {REMOTE_BASE_DIR} && docker compose ps")
    exec_remote(ssh, "curl -sf http://localhost:8088/api/v1/health || echo 'Health check failed'")


def show_logs(ssh, host_info, service="nocodb", lines=50):
    """显示容器日志"""
    print(f"\n{'='*60}")
    print(f"日志 [{service}] on {host_info['host']}")
    print(f"{'='*60}")
    exec_remote(
        ssh,
        f"cd {REMOTE_BASE_DIR} && docker compose logs --tail={lines} {service}",
    )


def full_deploy(host_info):
    """完整部署流程: 上传 + 启动"""
    ssh = create_ssh_client(host_info)
    try:
        upload_configs(ssh, host_info)
        success = start_services(ssh, host_info)
        if success:
            print(f"\n{'='*60}")
            print(f"部署成功!")
            print(f"  NocoDB: http://100.110.75.2:8088")
            print(f"  MinIO Console: http://100.110.75.2:9001")
            print(f"{'='*60}")
        else:
            print(f"\n[WARN] 部署命令已执行，但健康检查未通过，请检查日志")
            show_logs(ssh, host_info, "nocodb", 30)
    finally:
        ssh.close()
        print("[INFO] SSH 连接已关闭")


def main():
    parser = argparse.ArgumentParser(description="NocoDB oec-4-fnOS 部署脚本")
    parser.add_argument("-c", "--csv", default=DEFAULT_CSV, help="凭证 CSV 文件路径")
    parser.add_argument(
        "-a",
        "--action",
        default="full",
        choices=["upload", "start", "stop", "restart", "status", "logs", "full"],
        help="执行操作",
    )
    parser.add_argument("-s", "--service", default="nocodb", help="查看日志的服务名")
    parser.add_argument("-n", "--lines", type=int, default=50, help="日志行数")
    args = parser.parse_args()

    hosts = load_credentials(args.csv)
    host = hosts[0]  # 只有一台主机

    print(f"目标主机: {host['host']}:{host['port']}")
    print(f"操作: {args.action}\n")

    ssh = None
    try:
        if args.action == "full":
            full_deploy(host)
        else:
            ssh = create_ssh_client(host)
            if args.action == "upload":
                upload_configs(ssh, host)
            elif args.action == "start":
                start_services(ssh, host)
            elif args.action == "stop":
                stop_services(ssh, host)
            elif args.action == "restart":
                stop_services(ssh, host)
                time.sleep(3)
                start_services(ssh, host)
            elif args.action == "status":
                show_status(ssh, host)
            elif args.action == "logs":
                show_logs(ssh, host, args.service, args.lines)
    finally:
        if ssh:
            ssh.close()
            print("[INFO] SSH 连接已关闭")


if __name__ == "__main__":
    main()
