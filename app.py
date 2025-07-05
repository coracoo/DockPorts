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

# 配置日志
logging.basicConfig(level=logging.INFO)
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
    
    # 如果配置文件存在，直接返回
    if os.path.exists(CONFIG_FILE):
        print(f"配置文件已存在: {CONFIG_FILE}")
        return
    
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

def load_config():
    """加载配置文件"""
    try:
        with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"加载配置文件失败: {e}")
        # 返回默认配置
        return {
            "ssh": 22,
            "http": 80,
            "https": 443,
            "mysql": 3306,
            "postgresql": 5432,
            "redis": 6379,
            "mongodb": 27017,
            "elasticsearch": 9200,
            "app_settings": {
                "host": "0.0.0.0",
                "port": 7577,
                "debug": False
            }
        }

def save_config(config):
    """保存配置文件"""
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
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
        # 从配置文件获取端口映射
        config_ports = {k: v for k, v in config.items() if isinstance(v, int)}
        
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
        """获取host网络容器信息（带缓存，简化版本）"""
        import time
        
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
                        'exposed_ports': set()
                    }
                    
                    # 获取容器的ExposedPorts
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
                    
                    self.container_cache[container.name] = container_info
                    
        except Exception as e:
            logger.error(f"获取Docker容器信息失败: {e}")
        
        self.cache_timestamp = current_time
        return self.container_cache
    
    def get_port_analysis(self, start_port=1, end_port=65535):
        """分析端口使用情况并生成可视化数据"""
        docker_ports = self.get_docker_ports()
        host_ports_info = self.get_host_ports()
        
        # 合并所有已使用的端口
        used_ports = set(host_ports_info.keys())
        docker_port_map = {}
        
        for port_info in docker_ports:
            if port_info['port']:
                used_ports.add(port_info['port'])
                docker_port_map[port_info['port']] = port_info
        
        # 生成端口卡片数据
        port_cards = []
        sorted_ports = sorted(used_ports)
        
        logger.info(f"总共发现 {len(sorted_ports)} 个已使用端口")
        
        # 预处理：收集所有端口信息
        port_data_list = []
        for port in sorted_ports:
            if port in docker_port_map:
                # Docker容器端口
                docker_info = docker_port_map[port]
                card_data = {
                    'port': port,
                    'type': 'used',
                    'source': 'docker',
                    'protocol': 'TCP',  # Docker端口映射通常是TCP
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
                    'protocol': host_info.get('protocol', 'TCP'),
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
                    start_port = consecutive_unknown[0]['port']
                    end_port = consecutive_unknown[-1]['port']
                    
                    # 创建合并的端口卡片
                    merged_card = {
                        'type': 'unknown_range',
                        'start_port': start_port,
                        'end_port': end_port,
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
                # 如果最后一个是gap卡片，不需要再添加
                pass
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
        
        # 统计Docker容器数量
        docker_container_count = len(set(
            p.get('container', p.get('container_name', '')) 
            for p in port_cards 
            if p.get('source') == 'docker' and p.get('container')
        ))
        
        # 计算可用端口数量（65535减去已使用端口数）
        available_ports = 65535 - len(used_ports)
        
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
            'total_used': len(used_ports),
            'total_available': available_ports,
            'docker_containers': docker_container_count,
            'hidden_ports': hidden_ports
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
        port_data = port_monitor.get_port_analysis()
        
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
                        start_port = card.get('start_port', 0)
                        end_port = card.get('end_port', 0)
                        if start_port <= search_port <= end_port:
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
                        start_port = card.get('start_port', 0)
                        end_port = card.get('end_port', 0)
                        if start_port <= search_port <= end_port:
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
            
            # 检查端口是否已存在
            existing_service = None
            for service, existing_port in current_config.items():
                if existing_port == port:
                    existing_service = service
                    break
            
            if existing_service:
                # 更新现有端口的服务名称
                del current_config[existing_service]
                current_config[service_name] = port
            else:
                # 添加新的端口配置
                current_config[service_name] = port
            
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

if __name__ == '__main__':
    logger.info("启动DockPorts应用")
    app.run(host='0.0.0.0', port=7577, debug=True)