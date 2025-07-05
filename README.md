# DockPorts - 容器端口监控工具

一个现代化的Docker容器端口监控和可视化工具，帮助您轻松管理和监控NAS或服务器上的端口使用情况。

## ✨ 功能特性

- 🐳 **Docker集成**: 通过Docker API实时监控容器端口映射
- 🖥️ **系统监控**: 使用netstat监控主机端口使用情况
- 📊 **可视化展示**: 美观的卡片式界面，类似Docker Compose Maker风格
- 🔄 **实时刷新**: 支持手动和自动刷新端口信息
- 📱 **响应式设计**: 支持桌面和移动设备
- 🎯 **智能排序**: 端口按顺序排列，空隙用灰色卡片标注
- 🏷️ **来源标识**: 区分Docker容器端口和系统服务端口
- 👁️ **端口隐藏**: 支持隐藏不需要显示的端口，提供"已隐藏"标签页查看
- 📋 **批量操作**: 支持批量隐藏/取消隐藏端口范围
- 🎨 **虚拟端口**: 隐藏端口以虚线边框样式区分显示
- ⚡ **实时同步**: 隐藏/取消隐藏操作后立即更新显示状态

## 🖼️ 界面预览

界面采用现代化设计，包含：
- 蓝色渐变背景
- 卡片式端口展示
- 实时统计信息
- 响应式布局

## 🚀 快速开始

### 使用Docker Compose（推荐）

1. 克隆项目：
```bash
git clone <your-repo-url>
cd DockPorts
```

2. 启动服务：
```bash
docker-compose up -d
```

3. 访问应用：
打开浏览器访问 `http://localhost:7577`

### 使用Docker运行

```bash
docker build -t dockports .
docker run -d \
  --name dockports \
  -p 7577:7577 \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v /proc:/host/proc:ro \
  dockports
```

### 本地开发

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行应用：
```bash
python app.py
```

## 📋 系统要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- Linux系统（支持netstat命令）
- 端口7577可用

## 🔧 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TZ` | `Asia/Shanghai` | 时区设置 |
| `PYTHONUNBUFFERED` | `1` | Python输出缓冲设置 |

### 卷映射

| 主机路径 | 容器路径 | 说明 |
|----------|----------|------|
| `/var/run/docker.sock` | `/var/run/docker.sock` | Docker API访问（只读） |
| `/proc` | `/host/proc` | 系统进程信息（只读） |

## 📊 功能详解

### 端口监控

1. **Docker容器端口**：
   - 自动发现所有运行中的容器
   - 获取端口映射信息
   - 识别host网络模式容器

2. **系统端口**：
   - 使用netstat扫描监听端口
   - 支持TCP和UDP协议
   - 识别系统服务占用的端口

### 可视化展示

1. **端口卡片**：
   - 大号端口号显示
   - 容器名称和内部端口
   - 来源标识（Docker/系统）
   - 隐藏/取消隐藏按钮

2. **间隔卡片**：
   - 显示连续端口间的空隙
   - 标注可用端口数量
   - 灰色样式区分
   - 支持批量隐藏端口范围

3. **虚拟端口卡片**：
   - 虚线边框样式区分
   - 显示"已隐藏端口"标识
   - 支持取消隐藏操作

4. **标签页导航**：
   - 全部端口
   - 已使用端口
   - 可用端口
   - 已隐藏端口

5. **统计信息**：
   - 已使用端口总数
   - 可用端口总数
   - Docker容器数量

## 🛠️ API接口

### GET /api/ports
获取端口信息

**响应示例**：
```json
{
  "success": true,
  "data": {
    "port_cards": [
      {
        "port": 80,
        "type": "used",
        "container_name": "nginx",
        "container_port": "80/tcp",
        "source": "docker"
      }
    ],
    "total_used": 10,
    "total_available": 65525,
    "docker_containers": 5
  }
}
```

### GET /api/refresh
刷新端口信息

### 隐藏端口管理

#### GET /api/hidden-ports
获取隐藏端口列表

#### POST /api/hidden-ports
隐藏单个端口
```json
{
  "port": 8080
}
```

#### DELETE /api/hidden-ports
取消隐藏单个端口
```json
{
  "port": 8080
}
```

#### POST /api/hidden-ports/batch
批量隐藏端口
```json
{
  "ports": [8080, 8081, 8082]
}
```

#### DELETE /api/hidden-ports/batch
批量取消隐藏端口
```json
{
  "ports": [8080, 8081, 8082]
}
```

## 🔍 故障排除

### 常见问题

1. **无法连接Docker**：
   - 确保Docker socket已正确映射
   - 检查容器是否有访问Docker的权限

2. **netstat命令不可用**：
   - 确保容器内安装了net-tools包
   - 检查/proc目录是否正确映射

3. **端口7577被占用**：
   - 修改docker-compose.yml中的端口映射
   - 或停止占用该端口的服务

4. **隐藏端口功能异常**：
   - 检查config/hidden_ports.json文件权限
   - 确保容器有写入配置文件的权限
   - 查看浏览器控制台是否有JavaScript错误

5. **取消隐藏端口范围失败**：
   - 确保使用最新版本，包含批量取消隐藏API
   - 检查网络连接和API响应

### 日志查看

```bash
# 查看容器日志
docker-compose logs -f dockports

# 查看实时日志
docker logs -f dockports
```

## 🤝 贡献指南

欢迎提交Issue和Pull Request！

1. Fork项目
2. 创建功能分支
3. 提交更改
4. 推送到分支
5. 创建Pull Request

## 📝 更新日志

### v1.2.0 (最新)
- ✨ 新增端口隐藏功能，支持隐藏不需要显示的端口
- 📋 新增批量隐藏/取消隐藏端口范围功能
- 🎨 新增虚拟端口显示，隐藏端口以虚线边框区分
- 🏷️ 新增"已隐藏"标签页，专门查看隐藏的端口
- ⚡ 修复隐藏端口操作后需要手动刷新的问题，现在支持实时同步
- 🔧 修复取消隐藏端口范围时的JSON解析错误
- 🎯 优化隐藏端口的合并逻辑，与后端保持一致
- 🛠️ 新增完整的隐藏端口管理API接口

### v1.1.0
- 🐳 基础Docker容器端口监控功能
- 🖥️ 系统端口监控功能
- 📊 可视化端口展示界面
- 🔄 实时刷新功能

## 📄 许可证

MIT License

## 🙏 致谢

- 界面设计灵感来源于 [Docker Compose Maker](https://github.com/ajnart/dcm)
- 感谢Docker和Flask社区的支持

## 📞 联系方式

如有问题或建议，请通过以下方式联系：
- 提交GitHub Issue
- 发送邮件至项目维护者

---

**DockPorts** - 让端口管理变得简单高效！ 🚀