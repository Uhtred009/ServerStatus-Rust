#!/bin/bash

# 定义文件路径和服务名称
SCRIPT_URL="https://github.com/Uhtred009/ServerStatus-Rust/raw/master/autoupdatehaproxy.py"
SCRIPT_NAME="autoupdatehaproxy.py"
SERVICE_NAME="autoupdatehaproxy.service"
INSTALL_DIR="/usr/local/bin"
SERVICE_PATH="/etc/systemd/system/$SERVICE_NAME"

# 创建安装目录
mkdir -p "$INSTALL_DIR"

# 下载脚本
echo "正在下载脚本..."
if ! wget --no-check-certificate -qO "$INSTALL_DIR/$SCRIPT_NAME" "$SCRIPT_URL"; then
    echo "脚本下载失败，请检查网络连接或 URL 是否正确。"
    exit 1
fi

# 添加可执行权限
chmod +x "$INSTALL_DIR/$SCRIPT_NAME"

# 确保 Python 3 存在
if ! command -v python3 &>/dev/null; then
    echo "Python3 未安装，请先安装 Python3。"
    exit 1
fi

# 创建 systemd 服务文件
echo "正在创建 systemd 服务..."
cat > "$SERVICE_PATH" <<EOL
[Unit]
Description=Auto Update HAProxy Script
After=network.target

[Service]
ExecStart=/usr/bin/python3 $INSTALL_DIR/$SCRIPT_NAME
Restart=always
RestartSec=60
User=root

[Install]
WantedBy=multi-user.target
EOL

# 确保服务文件创建成功
if [[ ! -f "$SERVICE_PATH" ]]; then
    echo "服务文件创建失败，请检查权限。"
    exit 1
fi

# 重新加载 systemd 配置
echo "重新加载 systemd 配置..."
if ! systemctl daemon-reload; then
    echo "systemd 配置重新加载失败，请检查权限或配置。"
    exit 1
fi

# 启用并启动服务
echo "启用并启动服务..."
if ! systemctl enable "$SERVICE_NAME"; then
    echo "服务启用失败，请检查 systemctl 配置。"
    exit 1
fi

if ! systemctl start "$SERVICE_NAME"; then
    echo "服务启动失败，请检查脚本是否正确。"
    exit 1
fi

# 检查服务状态
echo "服务状态："
systemctl status "$SERVICE_NAME" --no-pager
