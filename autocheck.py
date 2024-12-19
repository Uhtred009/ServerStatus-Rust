import requests
import socket
import ssl
from urllib.parse import urlparse

# Webhook URLs
API_DOMAIN = "https://host.auto987.com/"  # 完整的 API 域名
FETCH_WEBHOOK_URL = "api/monitor/getHostAndPort"  # 获取域名和端口数据的 Webhook
REPORT_WEBHOOK_URL = "api/monitor/receivePortResults"  # 上报不通的域名和端口

# 完整的 API URL
FETCH_WEBHOOK_URL = API_DOMAIN + FETCH_WEBHOOK_URL
REPORT_WEBHOOK_URL = API_DOMAIN + REPORT_WEBHOOK_URL

# 设置 Basic Auth 用户名和密码
USERNAME = 'erzi'
PASSWORD = 'mmm7818456erzi.'

def fetch_domain_port_data():
    """
    从 Webhook 获取域名和端口数据。
    使用 Basic Auth 进行身份验证。
    """
    try:
        # 添加身份验证
        response = requests.get(FETCH_WEBHOOK_URL, auth=(USERNAME, PASSWORD))
        response.raise_for_status()  # 如果请求失败，会抛出异常
        data = response.json()  # 假设返回 JSON 数据
        if data.get("success"):  # 检查 success 标志
            return data.get("data", [])  # 返回 data 中的域名和端口列表
        else:
            print("Failed to fetch data: Success flag is False.")
            return []
    except Exception as e:
        print(f"Error fetching domain-port data: {e}")
        return []

def check_port_connectivity(server, port, timeout=5):
    """
    检测域名和端口是否可用，并验证 SSL 证书是否有效。
    """
    try:
        # 创建 socket 连接
        with socket.create_connection((server, port), timeout):
            # 如果连接成功，验证证书
            context = ssl.create_default_context()
            with context.wrap_socket(socket.socket(), server_hostname=server) as ssl_socket:
                ssl_socket.connect((server, port))
                
                # 获取证书信息
                cert = ssl_socket.getpeercert()
                
                # 如果获取到证书，表示 SSL/TLS 握手成功
                if cert:
                    print("SSL Certificate is valid.")
                    return True
                else:
                    print("SSL Certificate is not valid.")
                    return False
    except (socket.timeout, socket.error) as e:
        print(f"Socket connection failed: {e}")
        return False
    except ssl.SSLError as ssl_error:
        print(f"SSL handshake failed: {ssl_error}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False
def report_issue(failed_list, all_reachable=True):
    """
    上报不通的域名和端口到服务端。
    使用 Basic Auth 进行身份验证。
    如果没有失败的端口，也需要上报“所有端口正常”的消息。
    """
    try:
        # 标准化返回结构
        if all_reachable:
            payload = {
                "status": "success",
                "message": "All domains and ports are reachable",
                "failed_domains": []
            }
        else:
            payload = {
                "status": "failed",
                "message": "Some domains or ports failed",
                "failed_domains": failed_list
            }

        # 在 POST 请求中添加 Basic Auth 认证
        response = requests.post(REPORT_WEBHOOK_URL, json=payload, auth=(USERNAME, PASSWORD))
        response.raise_for_status()
        print(f"Successfully reported issues: {payload}")
    except Exception as e:
        print(f"Error reporting issues: {e}")

def main():
    # 获取域名和端口数据
    domain_port_list = fetch_domain_port_data()
    if not domain_port_list:
        print("No domain-port data retrieved.")
        return

    # 检测连通性
    failed_domains = []
    for entry in domain_port_list:
        name = entry.get("name")  # 获取域名/服务器名称
        server = entry.get("server")  # 获取服务器 IP 或域名
        port = entry.get("port")  # 获取端口号

        if not server or not port:
            print(f"Invalid entry: {entry}")
            continue
        
        # 检查端口是否可用
        if not check_port_connectivity(server, int(port)):
            print(f"Connection failed: {name} ({server}:{port})")
            failed_domains.append({"name": name, "server": server, "port": port})

    # 如果有失败的端口，报告不通的服务器和端口
    if failed_domains:
        report_issue(failed_domains, all_reachable=False)
    else:
        print("All domains and ports are reachable.")
        # 如果没有失败的端口，报告所有端口可用
        report_issue([], all_reachable=True)

if __name__ == "__main__":
    main()
