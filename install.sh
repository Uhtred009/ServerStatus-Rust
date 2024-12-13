#!/bin/bash
set -e

WORKSPACE="/usr/local/ServerStatus/client"
FILE_PATH="${WORKSPACE}/client.py"
SERVICE_FILE="/etc/systemd/system/status-client.service"

mkdir -p "$WORKSPACE"

echo "正在下载 client.py 文件..."
wget --no-check-certificate -qO "$FILE_PATH" "https://raw.githubusercontent.com/Uhtred009/ServerStatus-Rust/master/client.py"

if [[ ! -f "$FILE_PATH" ]]; then
    echo "文件下载失败，请检查网络连接或 URL 是否正确。"
    exit 1
fi

chmod +x "$FILE_PATH"

while getopts "u:" opt; do
    case $opt in
        u) USERNAME="$OPTARG" ;;
        *) echo "无效参数" && exit 1 ;;
    esac
done

if [[ -z "$USERNAME" ]]; then
    echo "未检测到用户名，请输入："
    while [[ -z "$USERNAME" ]]; do
        read -p "请输入用户名 (USER 参数): " USERNAME
        if [[ -z "$USERNAME" ]]; then
            echo "用户名不能为空，请重新输入。"
        fi
    done
fi

sed -i "s/^USER = .*$/USER = \"$USERNAME\"/" "$FILE_PATH"

echo "创建系统服务..."
cat > "$SERVICE_FILE" <<EOL
[Unit]
Description=ServerStatus Client
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=${WORKSPACE}
ExecStart=/usr/bin/python3 ${FILE_PATH}
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
EOL

echo "设置服务为开机自启动..."
systemctl daemon-reload
systemctl enable status-client

echo "启动服务..."
systemctl start status-client

echo "服务状态："
systemctl status status-client -n 10 --no-pager
