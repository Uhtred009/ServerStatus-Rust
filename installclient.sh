set -ex

WORKSPACE=/opt/ServerStatus
mkdir -p ${WORKSPACE}
cd ${WORKSPACE}

# 下载, arm 机器替换 x86_64 为 aarch64
OS_ARCH="x86_64"
latest_version=$(curl -m 10 -sL "https://api.github.com/repos/zdz/ServerStatus-Rust/releases/latest" | grep "tag_name" | head -n 1 | awk -F ":" '{print $2}' | sed 's/\"//g;s/,//g;s/ //g')

#wget --no-check-certificate -qO "client-${OS_ARCH}-unknown-linux-musl.zip"  "https://github.com/zdz/ServerStatus-Rust/releases/download/${latest_version}/client-${OS_ARCH}-unknown-linux-musl.zip"
wget --no-check-certificate -O "client-${OS_ARCH}-unknown-linux-musl.zip" "https://github.com/zdz/ServerStatus-Rust/releases/download/${latest_version}/client-${OS_ARCH}-unknown-linux-musl.zip"

unzip -o "client-${OS_ARCH}-unknown-linux-musl.zip"

# 提示用户输入用户名
read -p "请输入用户名(-u 参数): " USERNAME

# 检查用户是否输入了用户名
if [[ -z "$USERNAME" ]]; then
  echo "用户名不能为空！"
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
ExecStart=/opt/ServerStatus/stat_client -a "http://m.auto987.com:8080/report" -u $USERNAME -p mm.erzi
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
systemctl status stat_client
