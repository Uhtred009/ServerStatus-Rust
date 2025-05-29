import socket
import csv
import re
import subprocess
import time
import logging
from io import StringIO

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s: %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

def get_down_servers(socket_path):
    """从 HAProxy 套接字获取 Down 状态的服务器"""
    try:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
            sock.connect(socket_path)
            sock.sendall(b"show stat\n")
            response = b""
            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                response += chunk

            response_str = response.decode("utf-8")
            reader = csv.reader(StringIO(response_str))
            
            # 提取 Down 状态的服务器
            down_servers = []
            for row in reader:
                if len(row) <= 17 or row[0].startswith('#'):
                    continue
                if row[17] == 'DOWN' and row[1] not in ['FRONTEND', 'BACKEND']:
                    down_servers.append({
                        'backend': row[0],
                        'server': row[1],
                        'status': row[17],
                        'reason': row[62] if len(row) > 62 else ''
                    })
            return down_servers
    except Exception as e:
        logging.error(f"获取不可用服务器时出错: {e}")
        return []

def extract_backend_block(config_content, backend_name):
    """提取指定 backend 的配置块"""
    # 修改正则表达式，允许backend前面有空格
    pattern = rf'^\s*backend\s+{re.escape(backend_name)}\s*\n(.*?)(?=^\s*(?:backend|frontend)|\Z)'
    match = re.search(pattern, config_content, re.DOTALL | re.MULTILINE)
    return match.group(0) if match else None

def backend_has_backup(backend_block):
    """检查 backend 块中是否包含 backup 节点"""
    for line in backend_block.splitlines():
        if "backup" in line:
            logging.info(f"检测到 backup 节点: {line.strip()}")
            return True
    return False

def update_haproxy_config(config_path, servers):
    """更新 HAProxy 配置文件中的端口，仅修改包含 backup 节点的 backend"""
    try:
        with open(config_path, 'r') as f:
            config_content = f.read()

        modified = False
        for server in servers:
            backend = server['backend']
            name = server['server']
            logging.info(f"尝试更新: 后端={backend}, 名称={name}")

            # 提取 backend 块内容
            backend_block = extract_backend_block(config_content, backend)
            if not backend_block:
                logging.info(f"未找到 backend {backend}，跳过处理")
                continue

            # 检查是否包含 backup 节点
            if not backend_has_backup(backend_block):
                logging.info(f"backend {backend} 不包含 backup 节点，跳过处理")
                continue

            # 只在当前 backend 块中查找 server 行并提取当前端口
            pattern = rf'(server\s+{re.escape(name)}\s+\S+):(\d+)'
            matches = list(re.finditer(pattern, backend_block, re.MULTILINE))
            
            if matches:
                for match in matches:
                    full_match = match.group(0)
                    old_port = match.group(2)
                    new_port = str(int(old_port) + 1)
                    replaced_match = full_match.replace(f":{old_port}", f":{new_port}")

                    # 替换 backend 块中的 server 配置
                    backend_block = backend_block.replace(full_match, replaced_match)
                    modified = True
                    logging.info(f"更新 {name} 端口从 {old_port} 到 {new_port}")
            else:
                logging.warning(f"未找到匹配的服务器配置：{name}")

            # 将更新后的 backend 块替换回配置文件
            config_content = config_content.replace(
                extract_backend_block(config_content, backend),
                backend_block
            )

        if not modified:
            logging.warning("未对配置文件做任何更改。")
            return False

        # 写回配置文件
        with open(config_path, 'w') as f:
            f.write(config_content)

        logging.info("配置文件更新成功。")
        return True
    except Exception as e:
        logging.error(f"更新配置时出错: {e}")
        return False

def validate_haproxy_config(config_path):
    """验证 HAProxy 配置文件是否有效"""
    try:
        result = subprocess.run(['haproxy', '-c', '-f', config_path], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("HAProxy 配置文件验证通过")
            return True
        else:
            logging.error(f"HAProxy 配置文件验证失败: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"验证 HAProxy 配置文件时出错: {e}")
        return False

def reload_haproxy():
    """重载 HAProxy 配置"""
    try:
        result = subprocess.run(['systemctl', 'reload', 'haproxy'], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("HAProxy 重载成功")
        else:
            logging.error(f"HAProxy 重载失败: {result.stderr}")
    except Exception as e:
        logging.error(f"重载 HAProxy 时出错: {e}")

def main():
    socket_path = '/var/run/haproxy/admin.sock'
    config_path = '/etc/haproxy/haproxy.cfg'

    logging.info("启动 HAProxy 服务器恢复脚本")

    while True:
        # 获取 Down 状态的服务器
        down_servers = get_down_servers(socket_path)

        if down_servers:
            logging.info(f"发现 {len(down_servers)} 个 Down 服务器")
            for server in down_servers:
                logging.info(
                    f"Down 服务器 - 后端: {server['backend']}, 服务器: {server['server']}, "
                    f"状态: {server['status']}, 原因: {server['reason']}"
                )
            
            # 更新配置并验证配置文件
            if update_haproxy_config(config_path, down_servers):
                if validate_haproxy_config(config_path):
                    reload_haproxy()
                else:
                    logging.error("配置文件验证失败，取消重载 HAProxy")
        else:
            logging.info("未发现 Down 服务器")

        # 每小时运行一次
        time.sleep(21600)

if __name__ == '__main__':
    main()
