from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, TokenLog, VerificationCode, ApiKey, ApiCallLog, ModelInfo
from forms import EditProfileForm
from sqlalchemy import text, inspect
import secrets
import hashlib

# Create user blueprint
user = Blueprint("user", __name__)


@user.route("/dashboard")
@login_required
def dashboard():
    """User dashboard showing token stats and recent activity."""
    recent_logs = TokenLog.query.filter_by(user_id=current_user.id).order_by(TokenLog.timestamp.desc()).limit(5).all()
    
    # Calculate API call statistics
    total_api_calls = 0
    
    try:
        # Try to get API key stats using ORM
        api_keys = ApiKey.query.filter_by(user_id=current_user.id).all()
        total_api_calls = sum(key.total_calls or 0 for key in api_keys)
    except Exception as e:
        print(f"Error getting API key stats: {e}")
        # If ORM fails, try raw SQL
        from sqlalchemy import text
        try:
            # Get total calls
            result = db.session.execute(text("""
                SELECT COALESCE(SUM(total_calls), 0) as total_calls
                FROM api_keys 
                WHERE user_id = :user_id
            """), {"user_id": current_user.id})
            row = result.fetchone()
            if row:
                total_api_calls = row[0] or 0
        except Exception as e2:
            print(f"Raw SQL also failed: {e2}")
    
    return render_template("user_dashboard.html", 
                         user=current_user, 
                         recent_logs=recent_logs,
                         total_api_calls=total_api_calls)


@user.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    """User profile management - edit profile and change password."""
    form = EditProfileForm(obj=current_user)
    
    if request.method == "POST":
        action = request.form.get("action", "")
        
        if action == "profile":
            if form.validate_on_submit():
                current_user.username = form.username.data
                current_user.email = form.email.data
                db.session.commit()
                flash("Profile updated successfully.", "success")
            return redirect(url_for("user.profile"))
        
        elif action == "password":
            new_password = request.form.get("new_password", "").strip()
            confirm_password = request.form.get("confirm_password", "").strip()
            
            if not new_password:
                flash("Please enter a new password.", "warning")
            elif new_password != confirm_password:
                flash("Passwords do not match.", "danger")
            elif len(new_password) < 6:
                flash("Password must be at least 6 characters.", "warning")
            else:
                current_user.set_password(new_password)
                db.session.commit()
                flash("Password changed successfully.", "success")
            return redirect(url_for("user.profile"))
    
    return render_template("edit_profile.html", form=form)


@user.route("/change_password", methods=["GET", "POST"])
@login_required
def change_password():
    """Legacy route for password change (kept for compatibility)."""
    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")
        if new_password != confirm_password:
            flash("Passwords do not match.", "danger")
        elif len(new_password) < 6:
            flash("Password must be at least 6 characters.", "warning")
        else:
            current_user.set_password(new_password)
            db.session.commit()
            flash("Password changed successfully.", "success")
            return redirect(url_for("user.profile"))
    return render_template("change_password.html")


@user.route("/consume", methods=["POST"])
@login_required
def consume():
    """Route for user to consume tokens."""
    try:
        amount = int(request.form.get("amount", 0))
    except ValueError:
        flash("Please enter a valid number.", "warning")
        return redirect(url_for("user.dashboard"))
    
    if amount <= 0:
        flash("Amount must be greater than 0.", "warning")
        return redirect(url_for("user.dashboard"))
    
    if current_user.remaining_tokens < amount:
        flash("Insufficient tokens! Please contact admin.", "danger")
        return redirect(url_for("user.dashboard"))
    
    current_user.used_tokens += amount
    log = TokenLog(user_id=current_user.id, operator_id=current_user.id, action="consume", amount=amount)
    db.session.add(log)
    db.session.commit()
    flash(f"Successfully consumed {amount} Tokens.", "success")
    return redirect(url_for("user.dashboard"))


@user.route("/logs")
@login_required
def logs():
    """User's token operation log page."""
    logs = TokenLog.query.filter_by(user_id=current_user.id).order_by(TokenLog.timestamp.desc()).all()
    return render_template("user_logs.html", user=current_user, logs=logs)


@user.route("/redeem", methods=["GET", "POST"])
@login_required
def redeem():
    """Verification code redemption page for users to add tokens."""
    if request.method == "POST":
        code = request.form.get("code", "").strip().upper()
        
        if not code:
            flash("Please enter a verification code.", "warning")
        else:
            vc = VerificationCode.query.filter_by(code=code, is_used=False).first()
            if not vc:
                flash("Verification code does not exist or has been used.", "danger")
            else:
                vc.is_used = True
                vc.used_by = current_user.id
                from datetime import datetime
                vc.used_at = datetime.now()
                
                current_user.total_tokens += vc.tokens
                log = TokenLog(user_id=current_user.id, operator_id=current_user.id, action="add", amount=vc.tokens)
                db.session.add(log)
                db.session.commit()
                flash(f"Redemption successful! {vc.tokens} Tokens have been added to your account.", "success")
                return redirect(url_for("user.dashboard"))
    
    return render_template("user_redeem.html")


def generate_api_key():
    """Generate a secure API key."""
    # Generate 64-character hex string (32 bytes)
    return secrets.token_hex(32)


def hash_api_key(key):
    """Hash an API key for secure storage."""
    return hashlib.sha256(key.encode()).hexdigest()


@user.route("/api_keys")
@login_required
def api_keys():
    """User API key management page."""
    try:
        # Try normal query first
        keys = ApiKey.query.filter_by(user_id=current_user.id).order_by(ApiKey.created_at.desc()).all()
    except Exception as e:
        print(f"ORM query failed: {e}")  # For debugging
        
        # If query fails, try multiple SQL approaches
        
        # Approach 1: Try simplest query (only basic columns)
        try:
            sql = """
                SELECT id, user_id, key_hash, name, created_at
                FROM api_keys 
                WHERE user_id = :user_id 
                ORDER BY created_at DESC
            """
            result = db.session.execute(text(sql), {"user_id": current_user.id})
            
            keys = []
            for row in result:
                class MockKey:
                    pass
                key = MockKey()
                key.id = row[0]
                key.user_id = row[1]
                key.key_hash = row[2]
                key.name = row[3]
                key.created_at = row[4]
                key.total_calls = 0
                key.total_tokens_used = 0
                key.is_active = True
                key.last_used = None
                keys.append(key)
                
        except Exception as e1:
            print(f"Simple query also failed: {e1}")
            
            # Approach 2: Try query with COALESCE for optional columns
            try:
                sql = """
                    SELECT id, user_id, key_hash, name, created_at,
                           COALESCE(total_calls, 0) as total_calls,
                           COALESCE(total_tokens_used, 0) as total_tokens_used,
                           COALESCE(is_active, 1) as is_active
                    FROM api_keys 
                    WHERE user_id = :user_id 
                    ORDER BY created_at DESC
                """
                result = db.session.execute(text(sql), {"user_id": current_user.id})
                
                keys = []
                for row in result:
                    class MockKey:
                        pass
                    key = MockKey()
                    key.id = row[0]
                    key.user_id = row[1]
                    key.key_hash = row[2]
                    key.name = row[3]
                    key.created_at = row[4]
                    key.total_calls = row[5] if len(row) > 5 else 0
                    key.total_tokens_used = row[6] if len(row) > 6 else 0
                    key.is_active = bool(row[7] if len(row) > 7 else True)
                    key.last_used = None
                    keys.append(key)
                    
            except Exception as e2:
                print(f"COALESCE query failed: {e2}")
                # Last resort: empty list
                keys = []
    
    active_models = ModelInfo.query.filter_by(is_active=True).all()
    return render_template("user_api_keys.html", keys=keys, active_models=active_models)


@user.route("/api_keys/create", methods=["POST"])
@login_required
def create_api_key():
    """Create a new API key for the user."""
    name = request.form.get("name", "").strip()
    if not name:
        flash("请输入密钥名称", "warning")
        return redirect(url_for("user.api_keys"))
    
    # Generate API key
    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    
    # Check for hash collision (unlikely)
    if ApiKey.query.filter_by(key_hash=key_hash).first():
        flash("密钥生成冲突，请重试", "danger")
        return redirect(url_for("user.api_keys"))
    
    # Store prefix and suffix for display (first 8 and last 8 characters)
    key_prefix = raw_key[:8]
    key_suffix = raw_key[-8:]
    
    api_key = ApiKey(
        user_id=current_user.id,
        key_hash=key_hash,
        key_prefix=key_prefix,
        key_suffix=key_suffix,
        name=name,
        is_active=True
    )
    db.session.add(api_key)
    db.session.commit()
    
    # Show the raw key to user (only once) with copy button
    flash(f"""
    <div style='background: #f8f9fa; border-left: 4px solid #28a745; padding: 15px; margin: 10px 0; border-radius: 4px;'>
        <div style='display: flex; justify-content: space-between; align-items: flex-start;'>
            <div style='flex: 1;'>
                <h5 style='margin-top: 0; color: #28a745;'><strong>✅ API密钥创建成功！</strong></h5>
                <p style='margin-bottom: 10px;'><strong>请立即保存您的完整API密钥：</strong></p>
            </div>
            <button type='button' class='btn btn-sm btn-success copy-full-key-btn' 
                    style='margin-left: 15px;' 
                    data-clipboard-text='{raw_key}'
                    onclick='copyFullKey(this)'>
                <span>复制完整密钥</span>
            </button>
        </div>
        
        <div style='background: #fff; padding: 10px; border: 1px solid #ddd; border-radius: 4px; font-family: monospace; font-size: 14px; word-break: break-all; margin-bottom: 15px;'>
            {raw_key}
        </div>
        
        <div style='color: #dc3545; font-size: 13px;'>
            <strong>⚠️ 重要提示：</strong> 此密钥只会显示一次，页面刷新后将不再显示。请立即复制并妥善保存。
        </div>
        
        <div style='margin-top: 10px; font-size: 13px; color: #6c757d;'>
            密钥标识：<code style='background: #e9ecef; padding: 2px 6px; border-radius: 3px;'>sk-{key_prefix}************{key_suffix}</code>
            <br>密钥长度：64字符（32字节）
        </div>
    </div>
    
    <script>
    function copyFullKey(button) {{
        const textToCopy = button.getAttribute('data-clipboard-text');
        
        if (navigator.clipboard && window.isSecureContext) {{
            navigator.clipboard.writeText(textToCopy)
                .then(() => {{
                    const originalText = button.innerHTML;
                    button.innerHTML = '<span>✅ 已复制</span>';
                    button.classList.add('btn-success');
                    button.classList.remove('btn-primary');
                    
                    setTimeout(() => {{
                        button.innerHTML = originalText;
                        button.classList.remove('btn-success');
                        button.classList.add('btn-primary');
                    }}, 2000);
                }})
                .catch(err => {{
                    console.error('复制失败: ', err);
                    alert('复制失败，请手动选择文本复制');
                }});
        }} else {{
            const textArea = document.createElement('textarea');
            textArea.value = textToCopy;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();
            
            try {{
                document.execCommand('copy');
                const originalText = button.innerHTML;
                button.innerHTML = '<span>✅ 已复制</span>';
                button.classList.add('btn-success');
                button.classList.remove('btn-primary');
                
                setTimeout(() => {{
                    button.innerHTML = originalText;
                    button.classList.remove('btn-success');
                    button.classList.add('btn-primary');
                }}, 2000);
            }} catch (err) {{
                console.error('复制失败: ', err);
                alert('复制失败，请手动选择文本复制');
            }}
            
            document.body.removeChild(textArea);
        }}
    }}
    </script>
    """, "success")
    return redirect(url_for("user.api_keys"))


@user.route("/api_keys/<int:key_id>/revoke", methods=["POST"])
@login_required
def revoke_api_key(key_id):
    """Revoke (deactivate) an API key."""
    api_key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id).first_or_404()
    api_key.is_active = False
    db.session.commit()
    flash(f"API密钥 {api_key.name} 已撤销", "success")
    return redirect(url_for("user.api_keys"))


@user.route("/api_keys/<int:key_id>/delete", methods=["POST"])
@login_required
def delete_api_key(key_id):
    """Delete an API key (permanently)."""
    try:
        api_key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id).first_or_404()
    except Exception:
        # If ORM fails, try raw SQL
        result = db.session.execute(text("""
            SELECT id, name FROM api_keys WHERE id = :key_id AND user_id = :user_id
        """), {"key_id": key_id, "user_id": current_user.id})
        row = result.fetchone()
        if not row:
            flash("API密钥不存在", "danger")
            return redirect(url_for("user.api_keys"))
        
        # Create a mock object for deletion
        class MockKey:
            pass
        api_key = MockKey()
        api_key.id = row[0]
        api_key.name = row[1]
    
    key_name = api_key.name
    
    # Delete associated API call logs first
    try:
        db.session.execute(text("DELETE FROM api_call_logs WHERE api_key_id = :key_id"), {"key_id": key_id})
    except Exception:
        pass  # Table might not exist
    
    # Delete the API key
    try:
        db.session.execute(text("DELETE FROM api_keys WHERE id = :key_id"), {"key_id": key_id})
        db.session.commit()
        flash(f"API密钥 {key_name} 已永久删除", "success")
    except Exception as e:
        db.session.rollback()
        flash(f"删除失败: {e}", "danger")
    
    return redirect(url_for("user.api_keys"))


@user.route("/api_keys/<int:key_id>/logs")
@login_required
def api_key_logs(key_id):
    """View logs for a specific API key."""
    try:
        api_key = ApiKey.query.filter_by(id=key_id, user_id=current_user.id).first_or_404()
    except Exception:
        # If query fails, try raw SQL with dynamic column check
        inspector = inspect(db.engine)
        
        columns = []
        if 'api_keys' in inspector.get_table_names():
            columns = [col['name'] for col in inspector.get_columns('api_keys')]
        
        # Build dynamic SELECT statement
        select_fields = ["id", "user_id", "key_hash", "name", "created_at"]
        
        # Check for optional columns
        if 'total_calls' in columns:
            select_fields.append("total_calls")
        else:
            select_fields.append("0 as total_calls")
            
        if 'total_tokens_used' in columns:
            select_fields.append("total_tokens_used")
        else:
            select_fields.append("0 as total_tokens_used")
            
        if 'is_active' in columns:
            select_fields.append("is_active")
        else:
            select_fields.append("1 as is_active")
        
        sql = f"""
            SELECT {', '.join(select_fields)}
            FROM api_keys 
            WHERE id = :key_id AND user_id = :user_id
        """
        
        result = db.session.execute(text(sql), {"key_id": key_id, "user_id": current_user.id})
        
        row = result.fetchone()
        if not row:
            flash("API密钥不存在", "danger")
            return redirect(url_for("user.api_keys"))
        
        # Create a mock ApiKey-like object
        class MockKey:
            pass
        api_key = MockKey()
        api_key.id = row[0]
        api_key.user_id = row[1]
        api_key.key_hash = row[2]
        api_key.name = row[3]
        api_key.created_at = row[4]
        
        # Map remaining fields based on position
        if len(row) > 5:
            api_key.total_calls = row[5] if row[5] is not None else 0
        else:
            api_key.total_calls = 0
            
        if len(row) > 6:
            api_key.total_tokens_used = row[6] if row[6] is not None else 0
        else:
            api_key.total_tokens_used = 0
            
        if len(row) > 7:
            api_key.is_active = bool(row[7] if row[7] is not None else True)
        else:
            api_key.is_active = True
            
        api_key.last_used = None
    
    # Try to get logs
    try:
        logs = ApiCallLog.query.filter_by(api_key_id=key_id).order_by(ApiCallLog.timestamp.desc()).limit(100).all()
    except Exception:
        # If table doesn't exist, return empty list
        logs = []
    
    return render_template("user_api_key_logs.html", api_key=api_key, logs=logs)
