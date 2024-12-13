# -*- coding: utf-8 -*-
import socket
import time
import re
import os
import json
import subprocess
import collections
import platform

SERVER = "mm.auto987.com"
PORT = 35601
USER = "cn98"
PASSWORD = "doub.io"
INTERVAL = 1  # 更新间隔，单位：秒


def get_uptime():
    with open('/proc/uptime', 'r') as f:
        uptime = f.readline().split()[0]
    return int(float(uptime))


def get_memory():
    re_parser = re.compile(r'^(?P<key>\S*):\s*(?P<value>\d*)\s*kB')
    result = {}
    with open('/proc/meminfo') as f:
        for line in f:
            match = re_parser.match(line)
            if not match:
                continue
            key, value = match.groups()
            result[key] = int(value)

    MemTotal = result.get('MemTotal', 0)
    MemFree = result.get('MemFree', 0)
    Cached = result.get('Cached', 0)
    MemUsed = MemTotal - (MemFree + Cached)
    SwapTotal = result.get('SwapTotal', 0)
    SwapFree = result.get('SwapFree', 0)
    return MemTotal, MemUsed, SwapTotal, SwapFree


def get_hdd():
    try:
        output = subprocess.check_output(
            ['df', '-Tlm', '--total'], stderr=subprocess.DEVNULL
        ).decode("utf-8")
        total = output.splitlines()[-1]
        size, used = total.split()[2], total.split()[3]
        return int(size), int(used)
    except Exception:
        return 0, 0


def get_load():
    try:
        output = os.popen("ss -ant | grep ESTAB | wc -l").read()
        return float(output.strip())
    except Exception:
        return 0.0


def get_time():
    with open("/proc/stat", "r") as f:
        time_list = f.readline().split()[1:5]
    return [int(x) for x in time_list]


def delta_time():
    x = get_time()
    time.sleep(INTERVAL)
    y = get_time()
    return [y[i] - x[i] for i in range(len(x))]


def get_cpu():
    t = delta_time()
    total = sum(t)
    idle = t[-1]
    if total == 0:
        return 0
    return round((1 - idle / total) * 100, 2)


class Traffic:
    def __init__(self):
        self.rx = collections.deque(maxlen=10)
        self.tx = collections.deque(maxlen=10)

    def get(self):
        with open('/proc/net/dev', 'r') as f:
            net_dev = f.readlines()

        avgrx, avgtx = 0, 0
        for dev in net_dev[2:]:
            dev = dev.split(':')
            if dev[0].strip() == "lo" or "tun" in dev[0]:
                continue
            data = dev[1].split()
            avgrx += int(data[0])
            avgtx += int(data[8])

        self.rx.append(avgrx)
        self.tx.append(avgtx)

        if len(self.rx) > 1:
            avgrx = int((self.rx[-1] - self.rx[0]) / len(self.rx) / INTERVAL)
            avgtx = int((self.tx[-1] - self.tx[0]) / len(self.tx) / INTERVAL)

        return avgrx, avgtx


def liuliang():
    NET_IN, NET_OUT = 0, 0
    with open('/proc/net/dev', 'r') as f:
        for line in f:
            netinfo = re.findall(r'([^\s]+):[\s]*(\d+)', line)
            if netinfo and netinfo[0][0] != "lo":
                NET_IN += int(netinfo[0][1])
                NET_OUT += int(netinfo[-1][1])
    return NET_IN, NET_OUT


def get_network(ip_version):
    host = "ipv4.google.com" if ip_version == 4 else "ipv6.google.com"
    try:
        with socket.create_connection((host, 80), 2):
            return True
    except Exception:
        return False


if __name__ == '__main__':
    socket.setdefaulttimeout(30)
    while True:
        try:
            print("Connecting...")
            with socket.create_connection((SERVER, PORT), timeout=5) as s:
                data = s.recv(1024).decode('utf-8', errors='ignore')
                if "Authentication required" in data:
                    s.send(f"{USER}:{PASSWORD}\n".encode('utf-8'))
                    data = s.recv(1024).decode('utf-8', errors='ignore')
                    if "Authentication successful" not in data:
                        raise ConnectionError("Authentication failed")

                traffic = Traffic()
                traffic.get()
                while True:
                    stats = {
                        "cpu": get_cpu(),
                        "network_rx": traffic.get()[0],
                        "network_tx": traffic.get()[1],
                        "uptime": get_uptime(),
                        "load": get_load(),
                        "memory_total": get_memory()[0],
                        "memory_used": get_memory()[1],
                        "swap_total": get_memory()[2],
                        "swap_used": get_memory()[2] - get_memory()[3],
                        "hdd_total": get_hdd()[0],
                        "hdd_used": get_hdd()[1],
                        "network_in": liuliang()[0],
                        "network_out": liuliang()[1],
                    }
                    s.send(f"update {json.dumps(stats)}\n".encode('utf-8'))
                    time.sleep(INTERVAL)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(3)
