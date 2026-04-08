# Token Management System

> Professional token tracking and API management platform for LLM applications
> 
> English | [中文文档](README_CN.md)

## Overview

The Token Management System is a production-ready platform for tracking token usage across LLM (Large Language Model) applications. It provides comprehensive token accounting, API key management, and real-time usage analytics with an OpenAI-compatible interface.

## Key Features

### 🎯 Core Token Management
- **Token Accounting**: Track total, used, and remaining tokens per user
- **Real-time Deduction**: Automatic token consumption based on actual LLM usage
- **Overdraft Protection**: Allow usage when balance is positive (can go negative), block when zero/negative
- **Usage Analytics**: Detailed reports and visualizations of token consumption patterns

### 🔐 API Management
- **API Key Generation**: Create secure API keys with masked display format (`sk-08043***********************600c`)
- **OpenAI-Compatible Endpoint**: `/api/v1/chat/completions` works with standard OpenAI client libraries
- **Usage Tracking**: Log every API call with token counts, timestamps, and response metrics
- **Key Revocation**: Instantly revoke compromised or unused API keys

### 👥 User & Admin Portal
- **User Dashboard**: View token balance, usage history, and API key management
- **Admin Control**: Full user management, token allocation, and system configuration
- **Model Management**: Configure multiple LLM endpoints with custom pricing and limits
- **Verification Codes**: Generate redemption codes for token distribution

### 📊 Advanced Features
- **1:1 Token Ratio**: 1 model token consumed = 1 user token deducted (configurable)
- **Multi-Model Support**: Manage multiple LLM providers with individual configurations
- **Detailed Logging**: Complete audit trail of all token transactions and API calls
- **Automatic Database Setup**: Self-initializing database schema with backward compatibility

## Architecture

```
token_manager/
├── app.py                      # Main application entry point
├── config/                     # Configuration module
│   ├── __init__.py            # Flask app configuration
│   └── settings.py            # Project settings and constants
├── models.py                   # Database models (SQLAlchemy)
├── forms.py                    # Form definitions (WTForms)
├── requirements.txt            # Python dependencies
├── auth/                       # Authentication blueprint
│   └── __init__.py
├── admin/                      # Admin management blueprint
│   └── __init__.py
├── user/                       # User portal blueprint
│   └── __init__.py
├── api/                        # API endpoints blueprint
│   └── __init__.py
├── templates/                  # HTML templates (Jinja2)
│   ├── base.html
│   ├── admin_*.html
│   ├── user_*.html
│   └── auth_*.html
├── static/                     # Static assets
│   ├── css/style.css
│   └── js/main.js
└── README*.md                  # Documentation
```

## Quick Start

### Prerequisites
- Python 3.10+
- MySQL 5.7+ (or compatible database)
- pip or conda package manager

### Installation

1. **Clone and setup environment**
   ```bash
   # Create and activate virtual environment
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   venv\Scripts\activate     # Windows
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure database**
   - Ensure MySQL is running
   - Update database credentials in `config/__init__.py` if needed:
     ```python
     SQLALCHEMY_DATABASE_URI = "mysql+pymysql://username:password@localhost:3306/token_db"
     ```

4. **Run the application**
   ```bash
   python app.py
   ```
   The system will automatically:
   - Create database `token_db` if not exists
   - Initialize all tables with automatic schema migration
   - Create default admin user (username: `root`, password: `root123`)

5. **Access the application**
   - Web Interface: http://localhost:5000
   - API Base URL: http://localhost:5000/api/v1

## Configuration

### Token Settings
Edit `config/settings.py` to customize:

```python
# Resource type (set to 'token' for LLM token tracking)
RESOURCE_TYPE = "token"

# Database configuration
DATABASE_NAME = "token_db"

# Default admin credentials (change in production!)
DEFAULT_ADMIN_USERNAME = "root"
DEFAULT_ADMIN_PASSWORD = "root123"
DEFAULT_ADMIN_EMAIL = "root@example.com"
```

### Supported Resource Types
| Type | Display Name | Unit | Description |
|------|-------------|------|-------------|
| token | Tokens | 个 | LLM tokens (default) |
| inference | 推理次数 | 次 | Inference calls |
| image | 图像生成次数 | 张 | Image generations |
| api_call | API调用次数 | 次 | API calls |
| credit | 额度 | 点 | Credit points |
| custom | 配额 | 单位 | Custom resource |

## Usage Guide

### For Users
1. **Login** at http://localhost:5000/auth/login
2. **View Dashboard**: See token balance and usage statistics
3. **Redeem Tokens**: Use verification codes to add tokens
4. **Manage API Keys**: Create and revoke API keys for programmatic access
5. **View History**: Check detailed token usage logs

### For Administrators
1. **User Management**: Add/edit/delete users and allocate tokens
2. **Model Configuration**: Add LLM models with endpoints and pricing
3. **Code Generation**: Create token redemption codes
4. **System Monitoring**: View all transaction logs and API usage

### API Usage
1. **Create API Key** via web interface
2. **Make API Calls** using OpenAI-compatible format:
   ```bash
   curl -X POST http://localhost:5000/api/v1/chat/completions \
     -H "Authorization: Bearer YOUR_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{
       "model": "gpt-3.5-turbo",
       "messages": [{"role": "user", "content": "Hello!"}],
       "max_tokens": 100
     }'
   ```
3. **Check Usage**:
   ```bash
   curl -H "Authorization: Bearer YOUR_API_KEY" \
     http://localhost:5000/api/v1/usage
   ```

## API Reference

### Endpoints
- `POST /api/v1/chat/completions` - OpenAI-compatible chat completion
- `GET /api/v1/models` - List available models
- `GET /api/v1/usage` - Get token usage and balance

### Authentication
Use Bearer token authentication:
```http
Authorization: Bearer sk-08043***********************600c
```

### Token Deduction Logic
- **1:1 Consumption**: 1 model token = 1 user token deducted
- **Overdraft**: Users with positive balance can exceed balance (go negative), but zero/negative balance blocks new calls
- **Real-time Tracking**: Token counts updated immediately after API response

## Model Management

Administrators can configure multiple LLM models:

1. **Add Model**: Specify name, endpoint, and token price
2. **API Key Integration**: Optional API key for model endpoint authentication
3. **Token Limits**: Set maximum tokens per request
4. **Pricing**: Configure cost per token (supports fractional pricing)

## Security Features

- **Password Hashing**: bcrypt-based password storage
- **API Key Security**: SHA-256 hashed keys with masked display
- **CSRF Protection**: Built-in Flask-WTF protection
- **Role-based Access**: Strict separation between user and admin functions
- **Session Management**: Secure Flask-Login sessions

## Database Schema

The system automatically manages these tables:
- `users` - User accounts and token balances
- `token_logs` - All token transactions
- `verification_codes` - Redemption codes
- `model_info` - LLM model configurations
- `api_keys` - User API keys (hashed)
- `api_call_logs` - Detailed API call records

## Production Deployment

### Environment Variables
```bash
export SECRET_KEY="your-secret-key-here"
export DATABASE_URL="mysql+pymysql://user:pass@host:3306/dbname"
```

### Database Backups
Regularly backup your MySQL database:
```bash
mysqldump -u root -p token_db > backup-$(date +%Y%m%d).sql
```

### Monitoring
- Check `/admin/logs` for system activity
- Monitor database growth and performance
- Set up alerts for suspicious token usage patterns

## Troubleshooting

### Common Issues
1. **Database Connection Failed**
   - Verify MySQL is running
   - Check credentials in `config/__init__.py`
   - Ensure database user has CREATE DATABASE privileges

2. **API Key Not Working**
   - Verify key is active (not revoked)
   - Check token balance is not zero/negative
   - Ensure correct Authorization header format

3. **Model Endpoint Errors**
   - Verify endpoint URL is accessible
   - Check model API key (if required)
   - Confirm model is marked as active

### Logs
Application logs are printed to console. Check for:
- Database initialization messages
- API call details (token counts, responses)
- Error messages with stack traces

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with comprehensive tests
4. Submit a pull request

## License

This project is designed for internal enterprise use. Contact for licensing inquiries.

## Support

- **Documentation**: This README and `README_CN.md`
- **Issues**: Report bugs via GitHub Issues
- **Configuration**: All settings in `config/settings.py`
- **Database**: Automatic migration handles schema changes
