#!/bin/bash
set -e

# 定义文件路径和目标目录
WORKSPACE="/usr/local/ServerStatus/client"
FILE_PATH="${WORKSPACE}/client.py"
SERVICE_FILE="/etc/systemd/system/status-client.service"

# 创建目标目录
mkdir -p "$WORKSPACE"

# 下载文件
echo "正在下载 client.py 文件..."
wget --no-check-certificate -qO "$FILE_PATH" "https://raw.githubusercontent.com/Uhtred009/ServerStatus-Rust/master/client.py"

# 确保文件已下载
if [[ ! -f "$FILE_PATH" ]]; then
    echo "文件下载失败，请检查网络连接或 URL 是否正确。"
    exit 1
fi

# 设置文件权限
chmod +x "$FILE_PATH"

# 获取用户名
while getopts "u:" opt; do
    case $opt in
        u) USERNAME="$OPTARG" ;;
        *) echo "无效参数" && exit 1 ;;
    esac
done

# 如果没有提供用户名，则交互式提示
if [[ -z "$USERNAME" ]]; then
    while [[ -z "$USERNAME" ]]; do
        read -p "请输入用户名 (USER 参数): " USERNAME
        if [[ -z "$USERNAME" ]]; then
            echo "用户名不能为空，请重新输入。"
        fi
    done
fi

# 修改文件中的 USER 参数
sed -i "s/^USER = .*$/USER = \"$USERNAME\"/" "$FILE_PATH"

# 创建 systemd 服务文件
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

# 重新加载 systemd 并启用服务
echo "设置服务为开机自启动..."
systemctl daemon-reload
systemctl enable status-client

# 启动服务
echo "启动服务..."
systemctl start status-client

# 检查服务状态
echo "服务状态："
systemctl status status-client -n 10 --no-pager
