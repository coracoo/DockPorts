# 我的仓库

**1️⃣** ： 中文docker项目集成项目： [https://github.com/coracoo/awesome_docker_cn](https://github.com/coracoo/awesome_docker_cn)

**2️⃣** ： docker转compose：[https://github.com/coracoo/docker2compose](https://github.com/coracoo/docker2compose)

**3️⃣** ： 容器部署iSCSI，支持绿联极空间飞牛：[https://github.com/coracoo/d-tgtadm/](https://github.com/coracoo/d-tgtadm/)

**4️⃣** ： 容器端口检查工具： [https://github.com/coracoo/DockPorts/](https://github.com/coracoo/DockPorts)

# 我的频道

### 首发平台——什么值得买：

### [⭐点我关注](https://zhiyou.smzdm.com/member/9674309982/) 

### 微信公众号：

![关注](https://github.com/user-attachments/assets/9a1c4de0-2f08-413f-ab7f-d7d463af1698)

---

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

### 📦 镜像获取

DockPorts 提供多个镜像源，支持多平台架构：

| 镜像源 | 镜像地址 | 支持架构 | 说明 |
|--------|----------|----------|------|
| **GitHub Container Registry** | `ghcr.io/coracoo/dockports:latest` | `amd64`, `arm64`, `arm/v7` | 官方推荐，全球访问 |
| **阿里云容器镜像服务** | `registry.cn-hangzhou.aliyuncs.com/cherry4nas/dockports:latest` | `amd64`, `arm64`, `arm/v7` | 国内用户推荐，访问更快 |

**支持的平台：**
- `linux/amd64` - x86_64 架构（Intel/AMD 处理器）
- `linux/arm64` - ARM64 架构（Apple M1/M2、树莓派4等）
- `linux/arm/v7` - ARMv7 架构（树莓派3等）

### 使用Docker Compose（推荐）

1. 克隆项目：
```bash
git clone https://github.com/coracoo/DockPorts.git
cd DockPorts
```

2. **选择镜像源**（可选）：
   
   默认使用 GitHub 镜像，如需使用阿里云镜像，请修改 `docker-compose.yml`：
   ```yaml
   services:
     dockports:
       # 将下面这行：
       # image: ghcr.io/coracoo/dockports:latest
       # 替换为：
       image: registry.cn-hangzhou.aliyuncs.com/cherry4nas/dockports:latest
   ```

3. 启动服务：
```bash
docker-compose up -d
```

4. 访问应用：
打开浏览器访问 `http://localhost:7577`

### 使用Docker运行

#### 使用GitHub镜像（国外用户推荐）

```bash
# 使用默认端口7577
docker run -d \
  --name dockports \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/app/config \
  ghcr.io/coracoo/dockports:latest

# 使用自定义端口8080
docker run -d \
  --name dockports \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/app/config \
  -e DOCKPORTS_PORT=8080 \
  ghcr.io/coracoo/dockports:latest

# 启用调试模式
docker run -d \
  --name dockports \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/app/config \
  ghcr.io/coracoo/dockports:latest --debug
```

#### 使用阿里云镜像（国内用户推荐）

```bash
# 使用默认端口7577
docker run -d \
  --name dockports \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/app/config \
  registry.cn-hangzhou.aliyuncs.com/cherry4nas/dockports:latest

# 使用自定义端口8080
docker run -d \
  --name dockports \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/app/config \
  -e DOCKPORTS_PORT=8080 \
  registry.cn-hangzhou.aliyuncs.com/cherry4nas/dockports:latest

# 启用调试模式
docker run -d \
  --name dockports \
  --network host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/app/config \
  registry.cn-hangzhou.aliyuncs.com/cherry4nas/dockports:latest --debug
```

### 本地开发

1. 安装依赖：
```bash
pip install -r requirements.txt
```

2. 运行应用：
```bash
# 使用默认端口7577
python app.py

# 使用自定义端口
python app.py --port 8080

# 启用调试模式
python app.py --debug

# 查看帮助信息
python app.py --help
```

## 📋 系统要求

- Docker Engine 20.10+
- Docker Compose 2.0+
- Linux系统（支持netstat命令）
- 端口7577可用

## 🔧 技术架构

- **后端**: Python Flask + Docker API + psutil
- **前端**: HTML + CSS + JavaScript (原生)
- **容器化**: Docker + Docker Compose
- **CI/CD**: GitHub Actions + 多平台构建
- **镜像分发**: GitHub Container Registry + 阿里云容器镜像服务

### 🏗️ CI/CD 流程

项目采用 GitHub Actions 实现自动化构建和发布：

1. **触发条件**：
   - 推送版本标签（`v*.*.*`格式）
   - 手动触发工作流

2. **多平台构建**：
   - 使用 Docker Buildx 构建多架构镜像
   - 支持 `linux/amd64`、`linux/arm64`、`linux/arm/v7`
   - 利用 QEMU 实现跨平台编译

3. **镜像发布**：
   - **GitHub Container Registry**: `ghcr.io/coracoo/dockports`
   - **阿里云容器镜像服务**: `registry.cn-hangzhou.aliyuncs.com/cherry4nas/dockports`

4. **版本管理**：
   - 自动提取语义化版本号
   - 同时推送版本标签和 `latest` 标签
   - 包含完整的镜像元数据和标签

### Host网络容器端口检测机制

对于使用host网络模式的Docker容器，DockPorts采用多维度智能检测机制：

1. **ExposedPorts配置检测**
   - 从容器的`Config.ExposedPorts`中获取声明的端口
   - 解析端口格式（如`80/tcp`、`53/udp`）

2. **Healthcheck健康检查检测**
   - 解析`Config.Healthcheck.Test`命令
   - 使用正则表达式匹配`localhost:port`、`127.0.0.1:port`等模式
   - 自动提取健康检查中使用的端口号

3. **Entrypoint和Cmd命令检测**
   - 分析容器启动命令和入口点
   - 支持多种端口参数格式：
     - `--port=8080`、`--port 8080`
     - `-p=8080`、`-p 8080`
     - `--listen=8080`、`--bind=0.0.0.0:8080`
     - 通用`:port`模式

4. **环境变量检测**
   - 扫描容器环境变量中的端口配置
   - 识别`PORT`、`HTTP_PORT`、`LISTEN_PORT`等常见变量
   - 从变量值中提取端口号

5. **智能端口合并**
   - 将所有检测到的端口合并到`exposed_ports`集合
   - 提供详细的端口来源分类（健康检查、入口点、环境变量等）
   - 避免重复端口，确保数据准确性

## 🔧 配置说明

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `TZ` | `Asia/Shanghai` | 时区设置 |
| `PYTHONUNBUFFERED` | `1` | Python输出缓冲设置 |

## 🔧 配置说明

### 命令行参数

DockPorts 支持以下命令行参数来自定义运行配置：

| 参数 | 简写 | 默认值 | 说明 |
|------|------|--------|------|
| `--port` | `-p` | 7577 | Web服务端口 |
| `--host` | - | 0.0.0.0 | Web服务监听地址 |
| `--debug` | - | false | 启用调试模式 |
| `--help` | `-h` | - | 显示帮助信息 |

**使用示例：**
```bash
# 修改端口以避免冲突
python app.py --port 8080

# 在Docker中使用自定义端口
docker run -d --name dockports --network host \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/app/config \
  dockports --port 8080

# 在docker-compose中使用命令行参数
# 取消注释 docker-compose.yml 中的 command 行并修改参数
```

### 环境变量支持

除了命令行参数外，DockPorts还支持通过环境变量进行配置：

| 环境变量 | 对应参数 | 默认值 | 说明 |
|----------|----------|--------|------|
| `DOCKPORTS_PORT` | `--port` | 7577 | Web服务端口 |
| `DOCKPORTS_HOST` | `--host` | 0.0.0.0 | Web服务监听地址 |
| `DOCKPORTS_DEBUG` | `--debug` | false | 启用调试模式（设置为true、1或yes） |

**配置优先级：** 命令行参数 > 环境变量 > 默认值

**使用示例：**
```bash
# 使用环境变量设置端口
export DOCKPORTS_PORT=8080
python app.py

# 使用环境变量启用调试模式
export DOCKPORTS_DEBUG=true
python app.py

# Docker容器中使用环境变量
docker run -d --name dockports --network host \
  -e DOCKPORTS_PORT=8080 \
  -e DOCKPORTS_DEBUG=true \
  -v /var/run/docker.sock:/var/run/docker.sock:ro \
  -v ./config:/app/config \
  dockports

# docker-compose中使用环境变量
# 在docker-compose.yml的environment部分添加：
# environment:
#   - DOCKPORTS_PORT=8080
#   - DOCKPORTS_DEBUG=true
```

### 卷映射

| 主机路径 | 容器路径 | 说明 |
|----------|----------|------|
| `/var/run/docker.sock` | `/var/run/docker.sock` | Docker API访问（只读） |
| `./config` | `/app/config` | 配置文件目录 |

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

1. **镜像拉取失败**：
   - **GitHub镜像拉取慢**：尝试使用阿里云镜像
     ```bash
     docker pull registry.cn-hangzhou.aliyuncs.com/cherry4nas/dockports:latest
     ```
   - **阿里云镜像访问失败**：切换回GitHub镜像
     ```bash
     docker pull ghcr.io/coracoo/dockports:latest
     ```
   - **架构不匹配**：确认您的设备架构，镜像支持 `amd64`、`arm64`、`arm/v7`

2. **无法连接Docker**：
   - 确保Docker socket已正确映射
   - 检查容器是否有访问Docker的权限

3. **netstat命令不可用**：
   - 确保容器内安装了net-tools包
   - 检查/proc目录是否正确映射

4. **端口7577被占用**：
   - 修改docker-compose.yml中的端口映射
   - 或停止占用该端口的服务
   - 使用环境变量自定义端口：`-e DOCKPORTS_PORT=8080`

5. **隐藏端口功能异常**：
   - 检查config/hidden_ports.json文件权限
   - 确保容器有写入配置文件的权限
   - 查看浏览器控制台是否有JavaScript错误

6. **取消隐藏端口范围失败**：
   - 确保使用最新版本，包含批量取消隐藏API
   - 检查网络连接和API响应

7. **多架构部署问题**：
   - 树莓派等ARM设备确保使用正确的架构标签
   - 如遇到架构问题，可以手动指定平台：
     ```bash
     docker run --platform linux/arm64 ...
     ```

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

### v0.2.0 (最新)
- 🌐 **多平台支持**：新增 ARM64 和 ARMv7 架构支持
- 🚀 **阿里云镜像**：发布阿里云容器镜像服务，国内用户访问更快
- 🏗️ **CI/CD优化**：GitHub Actions 自动化多平台构建和发布
- 🔧 **端口范围锁定**：新增端口范围锁定功能，支持指定范围查看
- 📊 **前端优化**：修复端口范围锁定后的数据刷新问题
- 🐳 **镜像分发**：同时发布到 GitHub Container Registry 和阿里云
- 📖 **文档完善**：更新README，添加多镜像源使用说明
- 🔌 **协议区分**：支持UDP/TCP协议过滤和统计，提供协议切换按钮

### v0.1.2
- 🔧 修复自定义端口启动失败问题
- 📊 增强启动日志，显示实际使用的配置参数

### v0.1.1
- 🔧 增加host网络模式的处理
- 🐳 优化Docker容器端口检测机制

### v0.1.0 
- ⚙️ 新增命令行参数支持（--port, --host, --debug）
- 🔧 支持自定义Web服务端口，解决host网络模式下端口冲突问题
- 🐳 优化Docker镜像构建，支持ENTRYPOINT传参
- 📦 更新GitHub Actions配置，统一镜像名为DockPorts
- 👁️ 端口隐藏功能，支持隐藏不需要显示的端口
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
