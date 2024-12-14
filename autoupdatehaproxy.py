
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
                # 跳过表头和无效行
                if len(row) <= 17 or row[0].startswith('#'):
                    continue
                
                if row[17] == 'DOWN' and row[1] not in ['FRONTEND', 'BACKEND']:
                    # 添加到 Down 服务器列表
                    down_servers.append({
                        'backend': row[0],
                        'server': row[1],
                        'status': row[17],
                        'reason': row[62] if len(row) > 62 else ''
                    })
                    logging.info(f"找到 Down 服务器: {row}")
            
            return down_servers
    except Exception as e:
        logging.error(f"获取不可用服务器时出错: {e}")
        return []

def update_haproxy_config(config_path, servers):
    """更新 HAProxy 配置文件中的端口，仅匹配特定后端和服务器"""
    try:
        with open(config_path, 'r') as f:
            config_content = f.read()

        modified = False
        for server in servers:
            backend = server['backend']
            name = server['server']
            logging.info(f"尝试更新: 后端={backend}, 名称={name}")

            # 为了保证匹配后端和服务器名称，使用更加精确的正则表达式
            pattern = rf'(backend\s+{re.escape(backend)}.*?server\s+{re.escape(name)}\s+\S+):(\d+)'
            matches = list(re.finditer(pattern, config_content, re.DOTALL))
            
            if matches:
                for match in matches:
                    full_match = match.group(0)
                    old_port = match.group(2)
                    new_port = str(int(old_port) + 1)
                    replaced_match = full_match.replace(f":{old_port}", f":{new_port}")
                    config_content = config_content.replace(full_match, replaced_match)
                    modified = True
                    logging.info(f"更新 {name} 在 {backend} 中的端口从 {old_port} 到 {new_port}")
            else:
                logging.warning(f"未找到匹配的后端和服务器配置：{backend} / {name}")

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
    """验证 HAProxy 配置文件"""
    try:
        result = subprocess.run(['haproxy', '-c', '-f', config_path], capture_output=True, text=True)
        if result.returncode == 0:
            logging.info("配置文件验证成功")
            return True
        else:
            logging.error(f"配置文件验证失败: {result.stderr}")
            return False
    except Exception as e:
        logging.error(f"验证配置文件时出错: {e}")
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
            
            # 更新配置
            if update_haproxy_config(config_path, down_servers):
                # 验证配置文件
                if validate_haproxy_config(config_path):
                    reload_haproxy()
                else:
                    logging.error("跳过重载，因为配置文件验证失败")
        else:
            logging.info("未发现 Down 服务器")

        # 每小时检查一次
        time.sleep(3600)

if __name__ == '__main__':
    main()
