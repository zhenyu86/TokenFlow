from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, BooleanField, IntegerField, SubmitField, FloatField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from models import User


class RegistrationForm(FlaskForm):
    """User registration form."""
    username = StringField("用户名", validators=[DataRequired(), Length(min=3, max=25)])
    email = StringField("邮箱", validators=[DataRequired(), Email()])
    password = PasswordField("密码", validators=[DataRequired(), Length(min=6)])
    confirm = PasswordField("确认密码", validators=[DataRequired(), EqualTo("password")])
    submit = SubmitField("注册")

    def validate_username(self, field):
        """Check if username is already taken."""
        if User.query.filter_by(username=field.data).first():
            raise ValidationError("用户名已被使用")

    def validate_email(self, field):
        """Check if email is already registered."""
        if User.query.filter_by(email=field.data).first():
            raise ValidationError("邮箱已被注册")


class LoginForm(FlaskForm):
    """User login form."""
    username = StringField("用户名", validators=[DataRequired()])
    password = PasswordField("密码", validators=[DataRequired()])
    remember = BooleanField("记住我")
    submit = SubmitField("登录")


class AdminUserForm(FlaskForm):
    """Admin user management form."""
    username = StringField("用户名", validators=[DataRequired(), Length(min=3, max=25)])
    email = StringField("邮箱", validators=[DataRequired(), Email()])
    total_tokens = IntegerField("总量", validators=[DataRequired()])
    submit = SubmitField("保存")
    
    def validate_total_tokens(self, field):
        """Validate total tokens is not negative."""
        if field.data < 0:
            raise ValidationError("总量不能为负数")

    def __init__(self, original_username=None, *args, **kwargs):
        """Initialize form with original username for validation."""
        super().__init__(*args, **kwargs)
        self.original_username = original_username

    def validate_username(self, field):
        """Check if username is already taken (excluding current user)."""
        if field.data != self.original_username:
            if User.query.filter_by(username=field.data).first():
                raise ValidationError("用户名已被使用")


class EditProfileForm(FlaskForm):
    """User profile edit form."""
    username = StringField("用户名", validators=[DataRequired(), Length(min=3, max=25)])
    email = StringField("邮箱", validators=[DataRequired(), Email()])
    submit = SubmitField("保存")

    def __init__(self, original_username=None, original_email=None, *args, **kwargs):
        """Initialize form with original data for validation."""
        super().__init__(*args, **kwargs)
        self.original_username = original_username
        self.original_email = original_email

    def validate_username(self, field):
        """Check if username is already taken (excluding current user)."""
        if field.data != self.original_username:
            if User.query.filter_by(username=field.data).first():
                raise ValidationError("用户名已被使用")

    def validate_email(self, field):
        """Check if email is already registered (excluding current user)."""
        if field.data != self.original_email:
            if User.query.filter_by(email=field.data).first():
                raise ValidationError("邮箱已被注册")


class ModelForm(FlaskForm):
    """Model management form."""
    name = StringField("模型名称", validators=[DataRequired(), Length(min=2, max=100)])
    description = StringField("模型描述", validators=[Length(max=500)])
    api_endpoint = StringField("API端点", validators=[DataRequired(), Length(max=500)])
    api_key = StringField("API密钥", validators=[Length(max=500)])  # Optional
    price_per_token = FloatField("单价（每Token）", validators=[DataRequired()])
    max_tokens_per_request = IntegerField("每请求最大Tokens", validators=[DataRequired()])
    is_active = BooleanField("是否激活")
    submit = SubmitField("保存")
    
    def validate_price_per_token(self, field):
        """Validate price is non-negative."""
        if field.data < 0:
            raise ValidationError("单价不能为负数")
    
    def validate_max_tokens_per_request(self, field):
        """Validate max tokens is positive."""
        if field.data <= 0:
            raise ValidationError("每请求最大Tokens必须大于0")
    
    def validate_api_endpoint(self, field):
        """Validate endpoint is a valid URL."""
        endpoint = field.data
        if not (endpoint.startswith('http://') or endpoint.startswith('https://')):
            raise ValidationError("API端点必须以 http:// 或 https:// 开头")
        # Basic URL validation - could be more comprehensive
        if len(endpoint) < 10:  # Minimum reasonable URL length
            raise ValidationError("API端点太短")
