#!/bin/bash
set -ex

WORKSPACE=/opt/ServerStatus
mkdir -p ${WORKSPACE}
cd ${WORKSPACE}

# 下载, arm 机器替换 x86_64 为 aarch64
OS_ARCH="x86_64"
latest_version=$(curl -m 30 -sL "https://api.github.com/repos/zdz/ServerStatus-Rust/releases/latest" | grep "tag_name" | head -n 1 | awk -F ":" '{print $2}' | sed 's/\"//g;s/,//g;s/ //g')

if [[ -z "${latest_version}" ]]; then
    echo "无法获取最新版本信息，请检查网络或 GitHub API 的可用性"
    exit 1
fi

wget --no-check-certificate -O "client-${OS_ARCH}-unknown-linux-musl.zip" \
    "https://github.com/zdz/ServerStatus-Rust/releases/download/${latest_version}/client-${OS_ARCH}-unknown-linux-musl.zip"

if [[ $? -ne 0 ]]; then
    echo "下载失败，请检查网络连接和 URL 是否正确"
    exit 1
fi

unzip -o "client-${OS_ARCH}-unknown-linux-musl.zip"

# 检查解压是否成功
if [[ ! -f "stat_client" ]]; then
    echo "无法找到 stat_client 可执行文件，请检查解压内容"
    exit 1
fi

# 修改 stat_client.service 文件
SERVICE_FILE=/etc/systemd/system/stat_client.service

cat > $SERVICE_FILE <<EOL
[Unit]
Description=ServerStatus-Rust Client
After=network.target

[Service]
User=root
Group=root
Environment="RUST_BACKTRACE=1"
WorkingDirectory=/opt/ServerStatus
ExecStart=/opt/ServerStatus/stat_client -a "http://m.auto987.com:8989" -g zhuanxian -p mm.erzi
ExecReload=/bin/kill -HUP \$MAINPID
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOL

# 设置服务权限并启用自启动
chmod 644 $SERVICE_FILE
systemctl daemon-reload
systemctl enable stat_client

# 启动服务
systemctl start stat_client

# 检查服务状态
if systemctl is-active --quiet stat_client; then
    echo "服务已成功启动"
else
    echo "服务启动失败，请检查日志"
    systemctl status stat_client --no-pager
fi
