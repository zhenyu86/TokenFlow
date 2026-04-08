# Token 管理系统

> 专业的 LLM 应用 Token 统计与 API 管理平台
> 
> [English Documentation](README.md) | 中文文档

## 核心功能

### 🎯 Token 统计管理
- **Token 账户管理**：跟踪每个用户的总 Token、已用 Token、剩余 Token
- **实时扣费**：根据实际 LLM 使用量自动扣除 Token
- **透支保护**：余额为正时允许超额使用（可为负），零/负余额时阻止新调用
- **使用分析**：详细的 Token 消耗统计和可视化报表

### 🔐 API 管理
- **API 密钥生成**：创建安全的 API 密钥，显示为掩码格式（`sk-08043***********************600c`）
- **OpenAI 兼容接口**：`/api/v1/chat/completions` 支持标准 OpenAI 客户端库
- **使用追踪**：记录每次 API 调用的 Token 数量、时间戳和响应指标
- **密钥撤销**：立即撤销泄露或未使用的 API 密钥

### 👥 用户与管理员门户
- **用户控制台**：查看 Token 余额、使用历史、API 密钥管理
- **管理员控制**：完整的用户管理、Token 分配和系统配置
- **模型管理**：配置多个 LLM 端点，支持自定义定价和限制
- **兑换码系统**：生成用于 Token 分发的兑换码

### 📊 高级功能
- **1:1 Token 比例**：1 个模型 Token 消耗 = 1 个用户 Token 扣除（可配置）
- **多模型支持**：管理多个 LLM 提供商，各自独立配置
- **详细日志**：完整的 Token 交易和 API 调用审计跟踪
- **自动数据库设置**：自初始化数据库架构，支持向后兼容

## 系统架构

```
token_manager/
├── app.py                      # 主应用入口
├── config/                     # 配置模块
│   ├── __init__.py            # Flask 应用配置
│   └── settings.py            # 项目设置和常量
├── models.py                   # 数据库模型（SQLAlchemy）
├── forms.py                    # 表单定义（WTForms）
├── requirements.txt            # Python 依赖
├── auth/                       # 认证蓝图
│   └── __init__.py
├── admin/                      # 管理员管理蓝图
│   └── __init__.py
├── user/                       # 用户门户蓝图
│   └── __init__.py
├── api/                        # API 端点蓝图
│   └── __init__.py
├── templates/                  # HTML 模板（Jinja2）
│   ├── base.html
│   ├── admin_*.html
│   ├── user_*.html
│   └── auth_*.html
├── static/                     # 静态资源
│   ├── css/style.css
│   └── js/main.js
└── README*.md                  # 文档
```

## 快速开始

### 环境要求
- Python 3.10+
- MySQL 5.7+（或兼容数据库）
- pip 或 conda 包管理器

### 安装步骤

1. **克隆并设置环境**
   ```bash
   # 创建并激活虚拟环境
   python -m venv venv
   # Linux/Mac:
   source venv/bin/activate
   # Windows:
   venv\Scripts\activate
   ```

2. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

3. **配置数据库**
   - 确保 MySQL 正在运行
   - 如需修改数据库凭据，请更新 `config/__init__.py`：
     ```python
     SQLALCHEMY_DATABASE_URI = "mysql+pymysql://用户名:密码@localhost:3306/token_db"
     ```

4. **启动应用**
   ```bash
   python app.py
   ```
   系统将自动完成：
   - 创建数据库 `token_db`（如果不存在）
   - 初始化所有数据表，支持自动架构迁移
   - 创建默认管理员账户（用户名：`root`，密码：`root123`）

5. **访问应用**
   - 网页界面：http://localhost:5000
   - API 基础地址：http://localhost:5000/api/v1

## 配置说明

### Token 设置
编辑 `config/settings.py` 进行自定义：

```python
# 资源类型（设置为 'token' 进行 LLM Token 统计）
RESOURCE_TYPE = "token"

# 数据库配置
DATABASE_NAME = "token_db"

# 默认管理员凭据（生产环境请修改！）
DEFAULT_ADMIN_USERNAME = "root"
DEFAULT_ADMIN_PASSWORD = "root123"
DEFAULT_ADMIN_EMAIL = "root@example.com"
```

### 支持的资源类型
| 类型 | 显示名称 | 单位 | 描述 |
|------|----------|------|------|
| token | Tokens | 个 | LLM Tokens（默认）|
| inference | 推理次数 | 次 | 推理调用 |
| image | 图像生成次数 | 张 | 图像生成 |
| api_call | API调用次数 | 次 | API 调用 |
| credit | 额度 | 点 | 信用点 |
| custom | 配额 | 单位 | 自定义资源 |

## 使用指南

### 用户操作
1. **登录**：访问 http://localhost:5000/auth/login
2. **查看控制台**：查看 Token 余额和使用统计
3. **兑换 Token**：使用兑换码增加 Token
4. **管理 API 密钥**：创建和撤销用于程序访问的 API 密钥
5. **查看历史**：查看详细的 Token 使用日志

### 管理员操作
1. **用户管理**：添加/编辑/删除用户并分配 Token
2. **模型配置**：添加带端点和定价的 LLM 模型
3. **生成兑换码**：创建 Token 兑换码
4. **系统监控**：查看所有交易日志和 API 使用情况

### API 使用
1. **创建 API 密钥**：通过网页界面创建
2. **调用 API**：使用 OpenAI 兼容格式：
   ```bash
   curl -X POST http://localhost:5000/api/v1/chat/completions \
     -H "Authorization: Bearer 您的API密钥" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [{"role": "user", "content": "你好！"}],
       "max_tokens": 100
     }'
   ```
3. **检查使用情况**：
   ```bash
   curl -H "Authorization: Bearer 您的API密钥" \
     http://localhost:5000/api/v1/usage
   ```

## API 参考

### 端点
- `POST /api/v1/chat/completions` - OpenAI 兼容的聊天补全
- `GET /api/v1/models` - 列出可用模型
- `GET /api/v1/usage` - 获取 Token 使用情况和余额

### 认证
使用 Bearer Token 认证：
```http
Authorization: Bearer sk-08043***********************600c
```

### Token 扣费逻辑
- **1:1 消费比例**：1 个模型 Token = 1 个用户 Token 扣除
- **透支功能**：余额为正的用户可以超额使用（可为负），但零/负余额会阻止新调用
- **实时追踪**：API 响应后立即更新 Token 计数

## 模型管理

管理员可配置多个 LLM 模型：

1. **添加模型**：指定名称、端点和 Token 价格
2. **API 密钥集成**：可选的模型端点认证密钥
3. **Token 限制**：设置每个请求的最大 Token 数
4. **定价**：配置每个 Token 的成本（支持小数定价）

## 安全特性

- **密码哈希**：基于 bcrypt 的密码存储
- **API 密钥安全**：SHA-256 哈希密钥，显示为掩码格式
- **CSRF 保护**：内置 Flask-WTF 保护
- **基于角色的访问控制**：严格区分用户和管理员功能
- **会话管理**：安全的 Flask-Login 会话

## 数据库架构

系统自动管理以下表：
- `users` - 用户账户和 Token 余额
- `token_logs` - 所有 Token 交易记录
- `verification_codes` - 兑换码
- `model_info` - LLM 模型配置
- `api_keys` - 用户 API 密钥（哈希存储）
- `api_call_logs` - 详细的 API 调用记录

## 生产环境部署

### 环境变量
```bash
export SECRET_KEY="您的密钥"
export DATABASE_URL="mysql+pymysql://用户:密码@主机:3306/数据库名"
```

### 数据库备份
定期备份 MySQL 数据库：
```bash
mysqldump -u root -p token_db > backup-$(date +%Y%m%d).sql
```

### 监控
- 检查 `/admin/logs` 获取系统活动
- 监控数据库增长和性能
- 设置可疑 Token 使用模式警报

## 故障排除

### 常见问题
1. **数据库连接失败**
   - 确认 MySQL 正在运行
   - 检查 `config/__init__.py` 中的凭据
   - 确保数据库用户有 CREATE DATABASE 权限

2. **API 密钥无效**
   - 确认密钥处于活动状态（未撤销）
   - 检查 Token 余额不为零/负
   - 确保 Authorization 头格式正确

3. **模型端点错误**
   - 确认端点 URL 可访问
   - 检查模型 API 密钥（如需要）
   - 确认模型标记为活动状态

### 日志
应用日志输出到控制台。请检查：
- 数据库初始化消息
- API 调用详情（Token 计数、响应）
- 错误消息和堆栈跟踪

## 贡献指南

1. Fork 本仓库
2. 创建特性分支
3. 进行更改并包含全面测试
4. 提交 Pull Request

## 许可证

本项目设计用于企业内部使用。如需商业授权请联系。

## 支持

- **文档**：本文档和 `README.md`
- **问题反馈**：通过 GitHub Issues 报告错误
- **配置**：所有设置位于 `config/settings.py`
- **数据库**：自动迁移处理架构变更
