#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
DockPorts - 容器化NAS端口记录工具
主要功能：
1. 通过Docker API监控容器端口映射
2. 通过netstat监控主机端口使用情况
3. 可视化展示端口使用状态
"""

import docker
import subprocess
import json
import re
from flask import Flask, render_template, jsonify, request
from collections import defaultdict
import logging
from datetime import datetime, timedelta
import os
import socket
import time
from functools import lru_cache
import argparse

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(levelname)s:%(name)s:%(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# 配置文件路径
CONFIG_DIR = '/app/config'
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')
HIDDEN_PORTS_FILE = os.path.join(CONFIG_DIR, 'hidden_ports.json')
DEFAULT_CONFIG_FILE = '/app/config/config.json'

def init_config():
    """初始化配置文件"""
    import shutil
    
    # 确保配置目录存在
    os.makedirs(CONFIG_DIR, exist_ok=True)
    
    # 初始化主配置文件
    config_created = False
    if not os.path.exists(CONFIG_FILE):
        # 配置文件不存在时，从示例文件复制
        example_config_file = os.path.join(os.path.dirname(__file__), 'config.json.example')
        
        if os.path.exists(example_config_file):
            # 从示例文件复制配置
            shutil.copy2(example_config_file, CONFIG_FILE)
            print(f"配置文件已从示例文件复制: {CONFIG_FILE}")
        else:
            # 如果示例文件不存在，创建默认配置（向后兼容）
            default_config = {
                "远程登录": 22,
                "网页服务": 80,
                "安全网页": 443,
                "MySQL数据库": 3306,
                "PostgreSQL数据库": 5432,
                "Redis缓存": 6379,
                "MongoDB数据库": 27017,
                "搜索分析": 9200
            }
            
            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(default_config, f, indent=2, ensure_ascii=False)
            
            print(f"配置文件已创建（默认配置）: {CONFIG_FILE}")
        config_created = True
    else:
        print(f"配置文件已存在: {CONFIG_FILE}")
    
    # 初始化隐藏端口配置文件
    if not os.path.exists(HIDDEN_PORTS_FILE):
        # 创建空的隐藏端口配置文件
        with open(HIDDEN_PORTS_FILE, 'w', encoding='utf-8') as f:
            json.dump([], f, indent=2, ensure_ascii=False)
        print(f"隐藏端口配置文件已创建: {HIDDEN_PORTS_FILE}")
    else:
        print(f"隐藏端口配置文件已存在: {HIDDEN_PORTS_FILE}")

def load_config():
    """加载配置文件，支持UDP协议标记"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            raw_config = json.load(f)
        
        # 处理配置文件，支持name:port:udp格式
        processed_config = {}
        for key, value in raw_config.items():
            if isinstance(value, str) and ':' in value:
                # 解析name:port:protocol格式
                parts = value.split(':')
                if len(parts) >= 2:
                    try:
                        port = int(parts[-2] if len(parts) >= 3 else parts[-1])
                        protocol = parts[-1].upper() if len(parts) >= 3 and parts[-1].upper() in ['TCP', 'UDP'] else 'TCP'
                        processed_config[key] = {'port': port, 'protocol': protocol}
                    except ValueError:
                        processed_config[key] = value
                else:
                    processed_config[key] = value
            elif isinstance(value, int):
                # 默认为TCP协议
                processed_config[key] = {'port': value, 'protocol': 'TCP'}
            else:
                processed_config[key] = value
        
        return processed_config
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        # 返回默认配置
        return {
            "ssh": {'port': 22, 'protocol': 'TCP'},
            "http": {'port': 80, 'protocol': 'TCP'},
            "https": {'port': 443, 'protocol': 'TCP'},
            "mysql": {'port': 3306, 'protocol': 'TCP'},
            "postgresql": {'port': 5432, 'protocol': 'TCP'},
            "redis": {'port': 6379, 'protocol': 'TCP'},
            "mongodb": {'port': 27017, 'protocol': 'TCP'},
            "elasticsearch": {'port': 9200, 'protocol': 'TCP'},
            "app_settings": {
                "host": "0.0.0.0",
                "port": 7577,
                "debug": False
            }
        }

def save_config(config):
    """保存配置文件，支持UDP协议标记"""
    try:
        # 处理配置文件，将协议信息转换为字符串格式
        raw_config = {}
        for key, value in config.items():
            if isinstance(value, dict) and 'port' in value and 'protocol' in value:
                port = value['port']
                protocol = value['protocol']
                if protocol.upper() == 'UDP':
                    raw_config[key] = f"{port}:udp"
                else:
                    # TCP协议可以省略，直接使用端口号
                    raw_config[key] = port
            else:
                raw_config[key] = value
        
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(raw_config, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存配置文件失败: {e}")
        return False

def load_hidden_ports():
    """加载隐藏端口配置"""
    try:
        if os.path.exists(HIDDEN_PORTS_FILE):
            with open(HIDDEN_PORTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        return []
    except Exception as e:
        print(f"加载隐藏端口配置失败: {e}")
        return []

def save_hidden_ports(hidden_ports):
    """保存隐藏端口配置"""
    try:
        with open(HIDDEN_PORTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(hidden_ports, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"保存隐藏端口配置失败: {e}")
        return False

# 初始化配置
init_config()
config = load_config()

class PortMonitor:
    """端口监控类"""
    
    def __init__(self):
        """初始化Docker客户端"""
        try:
            self.docker_client = docker.from_env()
            logger.info("Docker客户端连接成功")
        except Exception as e:
            logger.error(f"Docker客户端连接失败: {e}")
            self.docker_client = None
        
        # 缓存相关属性
        self.container_cache = {}  # 容器信息缓存
        self.cache_timestamp = 0   # 缓存时间戳
        self.cache_ttl = 30        # 缓存生存时间（秒）
        
        # 默认端口服务映射
        self.default_ports = {
            21: "FTP", 22: "SSH", 23: "Telnet", 25: "SMTP", 53: "DNS", 67: "DHCP Server", 68: "DHCP Client",
            69: "TFTP", 80: "HTTP", 110: "POP3", 123: "NTP", 135: "RPC", 137: "NetBIOS Name", 138: "NetBIOS Datagram",
            139: "NetBIOS Session", 143: "IMAP", 161: "SNMP", 389: "LDAP", 443: "HTTPS", 445: "SMB", 465: "SMTPS",
            514: "Syslog", 587: "SMTP", 631: "IPP", 636: "LDAPS", 993: "IMAPS", 995: "POP3S", 1433: "SQL Server",
            1521: "Oracle", 3306: "MySQL", 3389: "RDP", 5432: "PostgreSQL", 5900: "VNC", 6379: "Redis",
            8080: "HTTP Proxy", 8443: "HTTPS Alt", 9200: "Elasticsearch", 27017: "MongoDB"
        }
    
    def get_docker_ports(self):
        """获取Docker容器端口映射信息"""
        ports_info = []
        
        if not self.docker_client:
            logger.warning("Docker客户端未连接")
            return ports_info
        
        try:
            containers = self.docker_client.containers.list()
            logger.info(f"发现 {len(containers)} 个运行中的容器")
            
            for container in containers:
                container_name = container.name
                ports = container.attrs.get('NetworkSettings', {}).get('Ports', {})
                
                for container_port, host_bindings in ports.items():
                    if host_bindings:
                        for binding in host_bindings:
                            host_port = int(binding['HostPort'])
                            ports_info.append({
                                'port': host_port,
                                'container_name': container_name,
                                'container_port': container_port,
                                'type': 'docker_mapped'
                            })
                            logger.debug(f"发现映射端口: {host_port} -> {container_name}:{container_port}")
                
                # 检查host网络模式的容器
                network_mode = container.attrs.get('HostConfig', {}).get('NetworkMode', '')
                if network_mode == 'host':
                    ports_info.append({
                        'port': None,  # host模式下无法直接获取端口
                        'container_name': container_name,
                        'container_port': 'host模式',
                        'type': 'docker_host'
                    })
                    logger.debug(f"发现host模式容器: {container_name}")
        
        except Exception as e:
            logger.error(f"获取Docker端口信息失败: {e}")
        
        return ports_info
    
    def get_host_ports(self):
        """获取主机端口使用情况（简化版本，仅检测端口占用）"""
        port_info = {}
        port_protocols = {}  # 用于跟踪每个端口的协议和IP版本
        
        # 获取host网络容器信息
        host_containers = self.get_host_network_containers_cached()
        
        try:
            # 使用netstat获取监听端口信息（不获取进程信息）
            result = subprocess.run(
                ['netstat', '-tuln'], 
                capture_output=True, 
                text=True, 
                check=True
            )
            
            logger.info("成功执行netstat命令")
            
            # 解析netstat输出
            for line in result.stdout.split('\n'):
                if not line.strip():
                    continue
                    
                parts = line.split()
                if len(parts) < 4:
                    continue
                
                # 匹配监听端口行
                if 'LISTEN' in line or 'udp' in line:
                    protocol = parts[0].upper()  # TCP/UDP
                    local_address = parts[3]
                    
                    # 解析协议和端口号
                    # 根据协议名称确定IP版本和协议类型
                    if protocol.endswith('6'):
                        # TCP6/UDP6 表示IPv6
                        protocol_type = protocol[:-1]  # 去掉末尾的6
                        ip_version = 'IPv6'
                    else:
                        # TCP/UDP 表示IPv4
                        protocol_type = protocol
                        ip_version = 'IPv4'
                    
                    if ':' in local_address:
                        # 解析端口号
                        if local_address.count(':') > 1 or protocol.endswith('6'):
                            # IPv6地址格式: [::]:port 或 [address]:port
                            if local_address.startswith('['):
                                port_part = local_address.split(']:')[-1]
                            else:
                                port_part = local_address.split(':')[-1]
                        else:
                            # IPv4格式: address:port
                            port_part = local_address.split(':')[-1]
                        
                        try:
                            port = int(port_part)
                        except ValueError:
                            continue
                    else:
                        continue
                    
                    # 检查是否为host网络容器的端口
                    container_name = None
                    for container_info in host_containers.values():
                        if port in container_info['exposed_ports']:
                            container_name = container_info['name']
                            break
                    
                    # 跟踪端口的协议和IP版本
                    if port not in port_protocols:
                        port_protocols[port] = {'protocols': set(), 'ip_versions': set()}
                    
                    port_protocols[port]['protocols'].add(protocol_type)
                    port_protocols[port]['ip_versions'].add(ip_version)
                    
                    # 如果端口已存在，更新信息
                    if port not in port_info:
                        port_info[port] = {
                            'port': port,
                            'protocol': protocol_type,
                            'ip_version': ip_version,
                            'address': local_address,
                            'service_name': self.get_service_name(port),
                            'container_name': container_name
                        }
                    
                    logger.debug(f"发现主机使用端口: {port} ({protocol}/{ip_version})")
            
            # 合并协议信息
            for port, info in port_info.items():
                protocols = port_protocols[port]['protocols']
                ip_versions = port_protocols[port]['ip_versions']
                
                # 合并协议，包含IP版本信息
                protocol_list = []
                for protocol in sorted(protocols):
                    if 'IPv4' in ip_versions and 'IPv6' in ip_versions:
                        # 同时支持IPv4和IPv6，显示TCP/UDP和TCP6/UDP6
                        protocol_list.extend([protocol, protocol + '6'])
                    elif 'IPv6' in ip_versions:
                        # 只支持IPv6
                        protocol_list.append(protocol + '6')
                    else:
                        # 只支持IPv4
                        protocol_list.append(protocol)
                
                # 去重并排序
                protocol_list = sorted(list(set(protocol_list)))
                info['protocol'] = '/'.join(protocol_list)
                
                # 移除单独的ip_version字段，信息已包含在protocol中
                del info['ip_version']
        
        except subprocess.CalledProcessError as e:
            logger.error(f"执行netstat命令失败: {e}")
        except Exception as e:
            logger.error(f"获取主机端口信息失败: {e}")
        
        return port_info
    
    def get_service_name(self, port):
        """根据端口号获取服务名称（仅使用配置文件映射）"""
        # 从配置文件获取端口映射，适配新的数据结构
        config_ports = {}
        for k, v in config.items():
            if isinstance(v, dict) and 'port' in v:
                config_ports[k] = v['port']
            elif isinstance(v, int):
                config_ports[k] = v
        
        # 创建端口到服务名的映射（反向映射）
        port_to_service = {v: k for k, v in config_ports.items()}
        
        # 使用配置文件中的端口映射
        if port in port_to_service:
            return port_to_service[port]
        
        # 使用默认端口映射
        if port in self.default_ports:
            return self.default_ports[port]
        
        # 如果都没有，返回未知
        return '未知服务'
    
    def get_host_network_containers_cached(self):
        """获取host网络容器信息（带缓存，增强版本）"""
        import time
        import re
        
        current_time = time.time()
        
        # 检查缓存是否有效
        if (current_time - self.cache_timestamp) < self.cache_ttl and self.container_cache:
            logger.debug("使用缓存的容器信息")
            return self.container_cache
        
        logger.debug("刷新容器信息缓存")
        self.container_cache = {}
        
        if not self.docker_client:
            return self.container_cache
        
        try:
            containers = self.docker_client.containers.list()
            for container in containers:
                # 检查容器的网络模式
                network_mode = container.attrs.get('HostConfig', {}).get('NetworkMode', '')
                if network_mode == 'host':
                    container_info = {
                        'name': container.name,
                        'id': container.id[:12],
                        'image': container.image.tags[0] if container.image.tags else 'unknown',
                        'exposed_ports': set(),
                        'potential_ports': set(),  # 从其他配置推断的可能端口
                        'healthcheck_ports': set(),  # 从健康检查推断的端口
                        'entrypoint_ports': set()   # 从入口点推断的端口
                    }
                    
                    # 1. 获取容器的ExposedPorts
                    try:
                        exposed_ports = container.attrs.get('Config', {}).get('ExposedPorts', {})
                        if exposed_ports:
                            for port_spec in exposed_ports.keys():
                                # 解析端口格式，如 "80/tcp", "53/udp"
                                if '/' in port_spec:
                                    port_num = int(port_spec.split('/')[0])
                                    container_info['exposed_ports'].add(port_num)
                                    logger.debug(f"容器 {container.name} 暴露端口: {port_num}")
                    except Exception as e:
                        logger.debug(f"获取容器 {container.name} ExposedPorts失败: {e}")
                    
                    # 2. 检查Healthcheck配置中的端口
                    try:
                        healthcheck = container.attrs.get('Config', {}).get('Healthcheck', {})
                        if healthcheck and 'Test' in healthcheck:
                            test_cmd = ' '.join(healthcheck['Test']) if isinstance(healthcheck['Test'], list) else str(healthcheck['Test'])
                            # 使用正则表达式查找端口号
                            port_matches = re.findall(r'(?:localhost|127\.0\.0\.1|0\.0\.0\.0):?(\d{1,5})', test_cmd)
                            for port_str in port_matches:
                                try:
                                    port_num = int(port_str)
                                    if 1 <= port_num <= 65535:
                                        container_info['healthcheck_ports'].add(port_num)
                                        container_info['potential_ports'].add(port_num)
                                        logger.debug(f"容器 {container.name} 健康检查端口: {port_num}")
                                except ValueError:
                                    continue
                    except Exception as e:
                        logger.debug(f"获取容器 {container.name} Healthcheck失败: {e}")
                    
                    # 3. 检查Entrypoint和Cmd中的端口
                    try:
                        # 检查Entrypoint
                        entrypoint = container.attrs.get('Config', {}).get('Entrypoint', [])
                        cmd = container.attrs.get('Config', {}).get('Cmd', [])
                        
                        # 合并entrypoint和cmd
                        full_command = []
                        if entrypoint:
                            full_command.extend(entrypoint if isinstance(entrypoint, list) else [entrypoint])
                        if cmd:
                            full_command.extend(cmd if isinstance(cmd, list) else [cmd])
                        
                        command_str = ' '.join(str(arg) for arg in full_command)
                        
                        # 查找常见的端口参数模式
                        port_patterns = [
                            r'--port[=\s]+(\d{1,5})',      # --port=8080 或 --port 8080
                            r'-p[=\s]+(\d{1,5})',          # -p=8080 或 -p 8080
                            r'--listen[=\s]+(\d{1,5})',    # --listen=8080
                            r'--bind[=\s]+[^:]*:(\d{1,5})', # --bind=0.0.0.0:8080
                            r':(\d{1,5})\b',               # 通用的 :端口 模式
                            r'PORT[=\s]+(\d{1,5})',        # PORT=8080
                            r'HTTP_PORT[=\s]+(\d{1,5})',   # HTTP_PORT=8080
                        ]
                        
                        for pattern in port_patterns:
                            matches = re.findall(pattern, command_str, re.IGNORECASE)
                            for port_str in matches:
                                try:
                                    port_num = int(port_str)
                                    if 1 <= port_num <= 65535:
                                        container_info['entrypoint_ports'].add(port_num)
                                        container_info['potential_ports'].add(port_num)
                                        logger.debug(f"容器 {container.name} 入口点端口: {port_num}")
                                except ValueError:
                                    continue
                                    
                    except Exception as e:
                        logger.debug(f"获取容器 {container.name} Entrypoint/Cmd失败: {e}")
                    
                    # 4. 检查环境变量中的端口
                    try:
                        env_vars = container.attrs.get('Config', {}).get('Env', [])
                        for env_var in env_vars:
                            if '=' in env_var:
                                key, value = env_var.split('=', 1)
                                # 查找端口相关的环境变量
                                if any(port_keyword in key.upper() for port_keyword in ['PORT', 'LISTEN', 'BIND']):
                                    try:
                                        # 尝试从环境变量值中提取端口号
                                        port_matches = re.findall(r'\b(\d{1,5})\b', value)
                                        for port_str in port_matches:
                                            port_num = int(port_str)
                                            if 1 <= port_num <= 65535:
                                                container_info['potential_ports'].add(port_num)
                                                logger.debug(f"容器 {container.name} 环境变量端口: {port_num} (来自 {key})")
                                    except (ValueError, AttributeError):
                                        continue
                    except Exception as e:
                        logger.debug(f"获取容器 {container.name} 环境变量失败: {e}")
                    
                    # 合并所有端口到exposed_ports中
                    container_info['exposed_ports'].update(container_info['potential_ports'])
                    
                    self.container_cache[container.name] = container_info
                    
        except Exception as e:
            logger.error(f"获取Docker容器信息失败: {e}")
        
        self.cache_timestamp = current_time
        return self.container_cache
    
    def get_port_analysis(self, start_port=1, end_port=65535, protocol_filter=None):
        """分析端口使用情况并生成可视化数据"""
        docker_ports = self.get_docker_ports()
        host_ports_info = self.get_host_ports()
        
        # 初始化端口卡片列表
        port_cards = []
        
        # 分别处理TCP和UDP端口
        tcp_ports = set()
        udp_ports = set()
        port_protocol_map = {}  # 端口到协议的映射
        
        # 处理主机端口信息，区分TCP和UDP，并应用端口范围过滤
        for port, info in host_ports_info.items():
            # 应用端口范围过滤
            if port < start_port or port > end_port:
                continue
                
            protocol = info.get('protocol', 'TCP')
            port_protocol_map[port] = protocol
            
            # 根据协议分类端口
            if 'TCP' in protocol.upper():
                tcp_ports.add(port)
            if 'UDP' in protocol.upper():
                udp_ports.add(port)
        
        # 处理Docker端口（通常是TCP），并应用端口范围过滤
        docker_port_map = {}
        for port_info in docker_ports:
            if port_info['port']:
                port = port_info['port']
                # 应用端口范围过滤
                if port < start_port or port > end_port:
                    continue
                    
                tcp_ports.add(port)  # Docker端口映射通常是TCP
                docker_port_map[port] = port_info
                if port not in port_protocol_map:
                    port_protocol_map[port] = 'TCP'
        
        # 根据协议过滤器选择端口
        if protocol_filter == 'TCP':
            filtered_ports = tcp_ports
            logger.info(f"TCP协议过滤: 发现 {len(tcp_ports)} 个TCP端口")
        elif protocol_filter == 'UDP':
            filtered_ports = udp_ports
            logger.info(f"UDP协议过滤: 发现 {len(udp_ports)} 个UDP端口")
        else:
            # 显示所有端口
            filtered_ports = tcp_ports.union(udp_ports)
            logger.info(f"总共发现 {len(filtered_ports)} 个已使用端口 (TCP: {len(tcp_ports)}, UDP: {len(udp_ports)})")
        
        sorted_ports = sorted(filtered_ports)
        
        # 预处理：收集所有端口信息
        port_data_list = []
        for port in sorted_ports:
            protocol = port_protocol_map.get(port, 'TCP')
            
            # 如果有协议过滤器，跳过不匹配的端口
            if protocol_filter and protocol_filter.upper() not in protocol.upper():
                continue
            
            if port in docker_port_map:
                # Docker容器端口
                docker_info = docker_port_map[port]
                card_data = {
                    'port': port,
                    'type': 'used',
                    'source': 'docker',
                    'protocol': protocol,
                    'container': docker_info['container_name'],
                    'process': f"Docker: {docker_info['container_name']}",
                    'image': docker_info.get('image', ''),
                    'container_port': docker_info['container_port'],
                    'service_name': docker_info['container_name']
                }
            else:
                # 系统服务端口
                host_info = host_ports_info.get(port, {})
                
                # 检查是否为host网络容器
                is_host_container = bool(host_info.get('container_name'))
                
                card_data = {
                    'port': port,
                    'type': 'used',
                    'source': 'docker' if is_host_container else 'system',
                    'protocol': protocol,
                    'service_name': host_info.get('service_name', '未知服务'),
                    'container': host_info.get('container_name'),
                    'is_host_network': is_host_container
                }
            port_data_list.append(card_data)
        
        # 处理连续的未知端口合并
        i = 0
        while i < len(port_data_list):
            current_port_data = port_data_list[i]
            
            # 检查是否为未知服务且可以开始合并
            if current_port_data['service_name'] == '未知服务':
                # 查找连续的未知端口
                consecutive_unknown = [current_port_data]
                j = i + 1
                
                while (j < len(port_data_list) and 
                       port_data_list[j]['service_name'] == '未知服务' and
                       port_data_list[j]['port'] == port_data_list[j-1]['port'] + 1):
                    consecutive_unknown.append(port_data_list[j])
                    j += 1
                
                # 如果有连续的未知端口（2个或以上），则合并
                if len(consecutive_unknown) >= 2:
                    range_start_port = consecutive_unknown[0]['port']
                    range_end_port = consecutive_unknown[-1]['port']
                    
                    # 创建合并的端口卡片
                    merged_card = {
                        'type': 'unknown_range',
                        'start_port': range_start_port,
                        'end_port': range_end_port,
                        'port_count': len(consecutive_unknown),
                        'source': consecutive_unknown[0]['source'],
                        'protocol': consecutive_unknown[0]['protocol'],
                        'service_name': '未知服务',
                        'container': consecutive_unknown[0].get('container'),
                        'is_host_network': consecutive_unknown[0].get('is_host_network', False)
                    }
                    port_cards.append(merged_card)
                    
                    # 跳过已处理的端口
                    i = j
                else:
                    # 单个未知端口，正常添加
                    port_cards.append(current_port_data)
                    i += 1
            else:
                # 非未知端口，正常添加
                port_cards.append(current_port_data)
                i += 1
            
            # 检查是否需要添加间隔卡片
            if i < len(port_data_list):
                # 获取当前卡片的最后一个端口
                last_card = port_cards[-1]
                if last_card['type'] == 'unknown_range':
                    current_last_port = last_card['end_port']
                else:
                    current_last_port = last_card.get('port')
                
                next_port = port_data_list[i]['port']
                gap = next_port - current_last_port - 1
                
                if gap > 0:
                    gap_card = {
                        'type': 'gap',
                        'start_port': current_last_port + 1,
                        'end_port': next_port - 1,
                        'available_count': gap
                    }
                    port_cards.append(gap_card)
        
        # 添加最后一个端口到65535的间隙
        if port_cards:
            # 获取最后一个卡片的最后端口
            last_card = port_cards[-1]
            
            if last_card['type'] == 'gap':
                # 如果最后一个是gap卡片，检查是否到达65535
                if last_card['end_port'] < end_port:
                    # 更新最后一个gap卡片到65535
                    last_card['end_port'] = end_port
                    last_card['available_count'] = last_card['end_port'] - last_card['start_port'] + 1
            else:
                if last_card['type'] == 'unknown_range':
                    last_port = last_card['end_port']
                else:
                    last_port = last_card.get('port', 0)
                
                if last_port < end_port:
                    final_gap = end_port - last_port
                    if final_gap > 0:
                        gap_card = {
                            'type': 'gap',
                            'start_port': last_port + 1,
                            'end_port': end_port,
                            'available_count': final_gap
                        }
                        port_cards.append(gap_card)
        else:
            # 如果没有任何端口卡片，创建一个从1到65535的完整gap
            gap_card = {
                'type': 'gap',
                'start_port': start_port,
                'end_port': end_port,
                'available_count': end_port - start_port + 1
            }
            port_cards.append(gap_card)
        
        # 统计Docker容器数量
        docker_container_count = len(set(
            p.get('container', p.get('container_name', '')) 
            for p in port_cards 
            if p.get('source') == 'docker' and p.get('container')
        ))
        
        # 计算可用端口数量（基于指定的端口范围）
        total_ports_in_range = end_port - start_port + 1
        if protocol_filter:
            # 如果有协议过滤器，可用端口数量是范围内总端口数减去该协议的已使用端口数
            available_ports = total_ports_in_range - len(filtered_ports)
        else:
            # 显示所有协议时，可用端口数量是范围内总端口数减去所有已使用端口数
            all_used_ports = tcp_ports.union(udp_ports)
            available_ports = total_ports_in_range - len(all_used_ports)
        
        # 过滤隐藏的端口
        hidden_ports = load_hidden_ports()
        if hidden_ports:
            filtered_port_cards = []
            for card in port_cards:
                should_hide = False
                
                if card['type'] == 'used':
                    # 检查单个端口是否被隐藏
                    if card['port'] in hidden_ports:
                        should_hide = True
                elif card['type'] == 'unknown_range':
                    # 检查端口范围是否有任何端口被隐藏
                    for port in range(card['start_port'], card['end_port'] + 1):
                        if port in hidden_ports:
                            should_hide = True
                            break
                
                if not should_hide:
                    filtered_port_cards.append(card)
            
            port_cards = filtered_port_cards
        
        return {
            'port_cards': port_cards,
            'total_used': len(filtered_ports),
            'total_available': available_ports,
            'tcp_used': len(tcp_ports),
            'udp_used': len(udp_ports),
            'docker_containers': docker_container_count,
            'hidden_ports': hidden_ports,
            'protocol_filter': protocol_filter
        }

# 创建端口监控实例
port_monitor = PortMonitor()

@app.route('/')
def index():
    """主页面"""
    return render_template('index.html')

@app.route('/api/ports')
def api_ports():
    """获取端口信息API"""
    try:
        # 获取协议过滤器参数
        protocol_filter = request.args.get('protocol', '').strip().upper()
        if protocol_filter not in ['TCP', 'UDP', '']:
            protocol_filter = None
        
        # 获取端口范围参数
        start_port = request.args.get('start_port', '1')
        end_port = request.args.get('end_port', '65535')
        
        # 验证端口范围参数
        try:
            start_port = int(start_port)
            end_port = int(end_port)
            
            # 确保端口范围有效
            if start_port < 1:
                start_port = 1
            if end_port > 65535:
                end_port = 65535
            if start_port > end_port:
                start_port, end_port = end_port, start_port
                
        except ValueError:
            # 如果参数无效，使用默认范围
            start_port = 1
            end_port = 65535
        
        port_data = port_monitor.get_port_analysis(start_port=start_port, end_port=end_port, protocol_filter=protocol_filter)
        
        # 处理搜索参数
        search = request.args.get('search', '').strip().lower()
        if search:
            # 保存原始的总已使用端口数
            original_total_used = port_data['total_used']
            
            filtered_cards = []
            for card in port_data['port_cards']:
                if card['type'] == 'used':
                    # 搜索端口号、进程名、服务名、容器名、协议
                    searchable_text = ' '.join([
                        str(card.get('port', '')),
                        card.get('process', '') or '',
                        card.get('service_name', '') or '',
                        card.get('container', '') or '',
                        card.get('protocol', '') or ''
                    ]).lower()
                    
                    if search in searchable_text:
                        filtered_cards.append(card)
                elif card['type'] == 'unknown_range':
                    # 搜索端口范围、服务名、容器名、协议
                    searchable_text = ' '.join([
                        f"{card.get('start_port', '')}-{card.get('end_port', '')}",
                        str(card.get('start_port', '')),
                        str(card.get('end_port', '')),
                        card.get('service_name', '') or '',
                        card.get('container', '') or '',
                        card.get('protocol', '') or ''
                    ]).lower()
                    
                    # 检查是否搜索范围内的单个端口号
                    is_match = search in searchable_text
                    if not is_match and search.isdigit():
                        search_port = int(search)
                        card_start_port = card.get('start_port', 0)
                        card_end_port = card.get('end_port', 0)
                        if card_start_port <= search_port <= card_end_port:
                            is_match = True
                    
                    if is_match:
                        filtered_cards.append(card)
                elif card['type'] == 'gap':
                    # 搜索可用端口范围
                    searchable_text = ' '.join([
                        f"{card.get('start_port', '')}-{card.get('end_port', '')}",
                        str(card.get('start_port', '')),
                        str(card.get('end_port', '')),
                        '可用', 'available', 'unused'
                    ]).lower()
                    
                    # 检查是否搜索范围内的单个端口号
                    is_match = search in searchable_text
                    if not is_match and search.isdigit():
                        search_port = int(search)
                        gap_start_port = card.get('start_port', 0)
                        gap_end_port = card.get('end_port', 0)
                        if gap_start_port <= search_port <= gap_end_port:
                            is_match = True
                    
                    if is_match:
                        filtered_cards.append(card)
            
            # 按端口排序
            filtered_cards = sorted(filtered_cards, key=lambda x: x.get('port', x.get('start_port', 0)))
            
            # 计算搜索结果中的已使用端口数
            filtered_used_count = len([card for card in filtered_cards if card['type'] in ['used', 'unknown_range']])
            
            # 更新统计信息
            port_data['port_cards'] = filtered_cards
            port_data['total_used'] = filtered_used_count
            # 搜索时，可用端口数量应该是总端口数减去所有已使用的端口数，而不是搜索结果数
            port_data['total_available'] = max(0, 65535 - original_total_used)
        
        return jsonify({
            'success': True,
            'data': port_data
        })
    except Exception as e:
        logger.error(f"API调用失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/config')
def api_get_config():
    """API接口：获取配置信息"""
    try:
        return jsonify(config)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/config', methods=['POST'])
def api_save_config():
    """API接口：保存配置信息"""
    # 重新加载配置
    global config
    
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': '无效的配置数据'}), 400
        
        # 检查是否是添加单个端口的请求
        if 'port' in data and 'service_name' in data:
            port = data['port']
            service_name = data['service_name'].strip()
            
            if not service_name:
                return jsonify({'error': '服务名称不能为空'}), 400
            
            # 验证端口号
            if not isinstance(port, int) or port < 1 or port > 65535:
                return jsonify({'error': '端口号必须在1-65535之间'}), 400
            
            # 加载当前配置
            current_config = load_config()
            
            # 检查端口是否已存在，适配新的数据结构
            existing_service = None
            for service, config_value in current_config.items():
                existing_port = None
                if isinstance(config_value, dict) and 'port' in config_value:
                    existing_port = config_value['port']
                elif isinstance(config_value, int):
                    existing_port = config_value
                
                if existing_port == port:
                    existing_service = service
                    break
            
            if existing_service:
                # 更新现有端口的服务名称
                del current_config[existing_service]
                current_config[service_name] = {'port': port, 'protocol': 'TCP'}
            else:
                # 添加新的端口配置
                current_config[service_name] = {'port': port, 'protocol': 'TCP'}
            
            # 保存配置
            if save_config(current_config):
                config = load_config()
                return jsonify({
                    'success': True, 
                    'message': f'端口 {port} 的服务名称已设置为 "{service_name}"'
                })
            else:
                return jsonify({'error': '配置保存失败'}), 500
        else:
            # 保存整个配置（原有功能）
            if save_config(data):
                config = load_config()
                return jsonify({'success': True, 'message': '配置保存成功'})
            else:
                return jsonify({'error': '配置保存失败'}), 500
                
    except Exception as e:
        logger.error(f"保存配置时出错: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/refresh')
def api_refresh():
    """刷新端口信息API"""
    try:
        # 重新初始化Docker客户端
        port_monitor.__init__()
        port_data = port_monitor.get_port_analysis()
        return jsonify({
            'success': True,
            'data': port_data,
            'message': '端口信息已刷新'
        })
    except Exception as e:
        logger.error(f"刷新失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hidden-ports')
def api_get_hidden_ports():
    """获取隐藏端口列表API"""
    try:
        hidden_ports = load_hidden_ports()
        return jsonify({
            'success': True,
            'data': hidden_ports
        })
    except Exception as e:
        logger.error(f"获取隐藏端口失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hidden-ports', methods=['POST'])
def api_hide_port():
    """隐藏端口API"""
    try:
        data = request.get_json()
        if not data or 'port' not in data:
            return jsonify({'error': '缺少端口参数'}), 400
        
        port = data['port']
        if not isinstance(port, int) or port < 1 or port > 65535:
            return jsonify({'error': '端口号必须在1-65535之间'}), 400
        
        hidden_ports = load_hidden_ports()
        if port not in hidden_ports:
            hidden_ports.append(port)
            hidden_ports.sort()
            
            if save_hidden_ports(hidden_ports):
                return jsonify({
                    'success': True,
                    'message': f'端口 {port} 已隐藏'
                })
            else:
                return jsonify({'error': '保存隐藏端口配置失败'}), 500
        else:
            return jsonify({
                'success': True,
                'message': f'端口 {port} 已经被隐藏'
            })
            
    except Exception as e:
        logger.error(f"隐藏端口失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hidden-ports', methods=['DELETE'])
def api_unhide_port():
    """取消隐藏端口API"""
    try:
        data = request.get_json()
        if not data or 'port' not in data:
            return jsonify({'error': '缺少端口参数'}), 400
        
        port = data['port']
        if not isinstance(port, int) or port < 1 or port > 65535:
            return jsonify({'error': '端口号必须在1-65535之间'}), 400
        
        hidden_ports = load_hidden_ports()
        if port in hidden_ports:
            hidden_ports.remove(port)
            
            if save_hidden_ports(hidden_ports):
                return jsonify({
                    'success': True,
                    'message': f'端口 {port} 已取消隐藏'
                })
            else:
                return jsonify({'error': '保存隐藏端口配置失败'}), 500
        else:
            return jsonify({
                'success': True,
                'message': f'端口 {port} 未被隐藏'
            })
            
    except Exception as e:
        logger.error(f"取消隐藏端口失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hidden-ports/batch', methods=['POST'])
def api_hide_ports_batch():
    """批量隐藏端口API"""
    try:
        data = request.get_json()
        if not data or 'ports' not in data:
            return jsonify({'error': '缺少端口列表参数'}), 400
        
        ports = data['ports']
        if not isinstance(ports, list):
            return jsonify({'error': '端口列表必须是数组'}), 400
        
        # 验证所有端口号
        for port in ports:
            if not isinstance(port, int) or port < 1 or port > 65535:
                return jsonify({'error': f'端口号 {port} 无效，必须在1-65535之间'}), 400
        
        hidden_ports = load_hidden_ports()
        new_hidden_count = 0
        
        for port in ports:
            if port not in hidden_ports:
                hidden_ports.append(port)
                new_hidden_count += 1
        
        hidden_ports.sort()
        
        if save_hidden_ports(hidden_ports):
            return jsonify({
                'success': True,
                'message': f'成功隐藏 {new_hidden_count} 个端口'
            })
        else:
            return jsonify({'error': '保存隐藏端口配置失败'}), 500
            
    except Exception as e:
        logger.error(f"批量隐藏端口失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/hidden-ports/batch', methods=['DELETE'])
def api_unhide_ports_batch():
    """批量取消隐藏端口API"""
    try:
        data = request.get_json()
        if not data or 'ports' not in data:
            return jsonify({'error': '缺少端口列表参数'}), 400
        
        ports = data['ports']
        if not isinstance(ports, list):
            return jsonify({'error': '端口列表必须是数组'}), 400
        
        # 验证所有端口号
        for port in ports:
            if not isinstance(port, int) or port < 1 or port > 65535:
                return jsonify({'error': f'端口号 {port} 无效，必须在1-65535之间'}), 400
        
        hidden_ports = load_hidden_ports()
        removed_count = 0
        
        for port in ports:
            if port in hidden_ports:
                hidden_ports.remove(port)
                removed_count += 1
        
        if save_hidden_ports(hidden_ports):
            return jsonify({
                'success': True,
                'message': f'成功取消隐藏 {removed_count} 个端口'
            })
        else:
            return jsonify({'error': '保存隐藏端口配置失败'}), 500
            
    except Exception as e:
        logger.error(f"批量取消隐藏端口失败: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def parse_args():
    """解析命令行参数和环境变量"""
    # 从环境变量获取默认值
    default_port = int(os.environ.get('DOCKPORTS_PORT', 7577))
    default_host = os.environ.get('DOCKPORTS_HOST', '0.0.0.0')
    default_debug = os.environ.get('DOCKPORTS_DEBUG', '').lower() in ('true', '1', 'yes')
    
    parser = argparse.ArgumentParser(description='DockPorts - 容器端口监控工具')
    parser.add_argument('--port', '-p', type=int, default=default_port,
                        help=f'Web服务端口 (默认: {default_port}, 可通过环境变量DOCKPORTS_PORT设置)')
    parser.add_argument('--host', type=str, default=default_host,
                        help=f'Web服务监听地址 (默认: {default_host}, 可通过环境变量DOCKPORTS_HOST设置)')
    parser.add_argument('--debug', action='store_true', default=default_debug,
                        help='启用调试模式 (可通过环境变量DOCKPORTS_DEBUG=true设置)')
    return parser.parse_args()

if __name__ == '__main__':
    # 解析命令行参数
    args = parse_args()
    
    # 显示配置信息
    logger.info("=== DockPorts 启动配置 ===")
    logger.info(f"监听地址: {args.host}")
    logger.info(f"监听端口: {args.port}")
    logger.info(f"调试模式: {args.debug}")
    
    # 显示环境变量信息（用于调试）
    env_port = os.environ.get('DOCKPORTS_PORT')
    env_host = os.environ.get('DOCKPORTS_HOST')
    env_debug = os.environ.get('DOCKPORTS_DEBUG')
    
    if env_port or env_host or env_debug:
        logger.info("=== 环境变量配置 ===")
        if env_port:
            logger.info(f"DOCKPORTS_PORT: {env_port}")
        if env_host:
            logger.info(f"DOCKPORTS_HOST: {env_host}")
        if env_debug:
            logger.info(f"DOCKPORTS_DEBUG: {env_debug}")
    
    logger.info("=========================")
    
    # 验证端口范围
    if not (1 <= args.port <= 65535):
        logger.error(f"端口号 {args.port} 无效，必须在1-65535之间")
        exit(1)
    
    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except OSError as e:
        if "Address already in use" in str(e):
            logger.error(f"端口 {args.port} 已被占用，请使用 --port 参数指定其他端口")
            logger.info("例如: python app.py --port 8080")
        else:
            logger.error(f"启动失败: {e}")
        exit(1)
    except KeyboardInterrupt:
        logger.info("应用已停止")
    except Exception as e:
        logger.error(f"应用运行时出错: {e}")
        exit(1)