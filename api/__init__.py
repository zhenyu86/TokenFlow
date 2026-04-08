from flask import Blueprint, request, jsonify, current_app
from flask_login import current_user
from models import db, ApiKey, ApiCallLog, ModelInfo, User, TokenLog
import requests
import json
import hashlib
import math
from datetime import datetime


def estimate_tokens(text):
    """Estimate token count for text (simplified).
    
    In production, replace with actual tokenizer (e.g., tiktoken for OpenAI models).
    Default: 1 token ≈ 4 characters for English text.
    """
    return len(str(text)) // 4 if text else 0

api = Blueprint("api", __name__, url_prefix="/api/v1")


def verify_api_key():
    """Verify API key from Authorization header."""
    auth_header = request.headers.get("Authorization")
    if not auth_header:
        return None, "Missing Authorization header"
    
    # Expecting "Bearer <token>" or just token
    parts = auth_header.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        api_key = parts[1]
    elif len(parts) == 1:
        api_key = parts[0]
    else:
        return None, "Invalid Authorization header format"
    
    # Hash the provided key
    key_hash = hashlib.sha256(api_key.encode()).hexdigest()
    
    # Find API key
    api_key_obj = ApiKey.query.filter_by(key_hash=key_hash, is_active=True).first()
    print(f"[API] API key verification: hash={key_hash[:16]}..., found={api_key_obj is not None}, active={api_key_obj.is_active if api_key_obj else False}")
    if not api_key_obj:
        return None, "Invalid or inactive API key"
    
    # Update last used timestamp
    api_key_obj.last_used = datetime.utcnow()
    db.session.commit()
    
    return api_key_obj, None


@api.route("/chat/completions", methods=["POST"])
def chat_completions():
    """OpenAI-compatible chat completions endpoint."""
    # Verify API key
    print(f"[API] Starting chat completion request")
    api_key_obj, error = verify_api_key()
    if error:
        print(f"[API] API key verification failed: {error}")
        return jsonify({"error": error}), 401
    
    user = User.query.get(api_key_obj.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 500
    
    # Parse request
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid JSON"}), 400
    
    # Extract parameters
    model_name = data.get("model")
    messages = data.get("messages")
    max_tokens = data.get("max_tokens", 512)
    temperature = data.get("temperature", 0.7)
    
    if not model_name:
        return jsonify({"error": "Model is required"}), 400
    if not messages:
        return jsonify({"error": "Messages are required"}), 400
    
    # Get model info
    model = ModelInfo.query.filter_by(name=model_name, is_active=True).first()
    print(f"[API] Model lookup: name={model_name}, found={model is not None}, endpoint={model.api_endpoint if model else None} (using 1:1 token ratio)")
    if not model:
        return jsonify({"error": "Model not found or inactive"}), 400
    if not model.api_endpoint:
        return jsonify({"error": "Model endpoint not configured"}), 400
    
    # Calculate estimated token cost (simplified)
    estimated_prompt_tokens = sum(estimate_tokens(m) for m in messages)
    estimated_total_tokens = estimated_prompt_tokens + max_tokens
    cost_tokens = estimated_total_tokens
    print(f"[API] Estimated tokens: prompt={estimated_prompt_tokens}, max_response={max_tokens}, total={estimated_total_tokens}, cost_tokens: {cost_tokens} (1:1 ratio)")
    
    # Check user balance (allow overdraft if user still has positive balance)
    print(f"[API] User {user.id} balance check: remaining_tokens={user.remaining_tokens}, cost_tokens={cost_tokens}")
    
    if user.remaining_tokens <= 0:
        print(f"[API] REJECT: User has zero or negative balance: {user.remaining_tokens}")
        return jsonify({"error": "Insufficient tokens"}), 402
    
    if user.remaining_tokens < cost_tokens:
        print(f"[API] WARNING: Insufficient tokens: {user.remaining_tokens} < {cost_tokens}, allowing overdraft")
    
    # Prepare request to actual model endpoint
    headers = {
        "Content-Type": "application/json",
    }
    
    # If model endpoint requires authentication, add it here
    if model.api_key:
        headers["Authorization"] = f"Bearer {model.api_key}"
    
    payload = {
        "model": model_name,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    
    try:
        # Forward request to actual model
        print(f"[API] Forwarding request to model endpoint: {model.api_endpoint}")
        response = requests.post(
            model.api_endpoint,
            headers=headers,
            json=payload,
            timeout=30
        )
        status_code = response.status_code
        print(f"[API] Model response status: {status_code}")
        
        # Parse response
        if response.ok:
            result = response.json()
            # Debug: print response structure to check for usage field
            print(f"[API] Response keys: {list(result.keys())}")
            
            # Extract token usage from response if available
            usage = result.get("usage", {})
            print(f"[API] Usage field: {usage}")
            
            if usage:
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
                total_tokens = usage.get("total_tokens", 0)
                print(f"[API] Real token usage from API: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")
            else:
                # If no usage info, use a better estimation
                response_text = str(result)
                estimated_completion_tokens = estimate_tokens(response_text)
                # Use the original prompt estimation (without max_tokens)
                prompt_tokens = estimated_prompt_tokens
                completion_tokens = estimated_completion_tokens
                total_tokens = prompt_tokens + completion_tokens
                print(f"[API] No usage field, estimated: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}")
            
            # Calculate actual cost: 1 model token = 1 user token
            actual_cost_tokens = total_tokens
            print(f"[API] Token usage: prompt={prompt_tokens}, completion={completion_tokens}, total={total_tokens}, actual_cost={actual_cost_tokens} (1:1 ratio)")
            
            # Deduct tokens from user
            user.used_tokens += actual_cost_tokens
            print(f"[API] Deducted {actual_cost_tokens} tokens from user {user.id} (balance: {user.remaining_tokens})")
            
            # Update API key stats
            api_key_obj.total_calls += 1
            api_key_obj.total_tokens_used += total_tokens
            print(f"[API] API key {api_key_obj.id} stats: total_calls={api_key_obj.total_calls}, total_tokens_used={api_key_obj.total_tokens_used}")
            
            # Log token consumption
            token_log = TokenLog(
                user_id=user.id,
                operator_id=user.id,
                action="api_call",
                amount=actual_cost_tokens
            )
            db.session.add(token_log)
            
            # Log API call
            log = ApiCallLog(
                api_key_id=api_key_obj.id,
                user_id=user.id,
                model_name=model_name,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                cost_tokens=actual_cost_tokens,
                endpoint=model.api_endpoint,
                status_code=status_code
            )
            db.session.add(log)
            db.session.commit()
            
            # Return the original response
            return jsonify(result)
        else:
            # Log failed call
            log = ApiCallLog(
                api_key_id=api_key_obj.id,
                user_id=user.id,
                model_name=model_name,
                prompt_tokens=0,
                completion_tokens=0,
                total_tokens=0,
                cost_tokens=0,
                endpoint=model.api_endpoint,
                status_code=status_code
            )
            db.session.add(log)
            db.session.commit()
            
            return jsonify({"error": f"Model request failed: {response.text}"}), status_code
            
    except requests.exceptions.RequestException as e:
        # Log error
        log = ApiCallLog(
            api_key_id=api_key_obj.id,
            user_id=user.id,
            model_name=model_name,
            prompt_tokens=0,
            completion_tokens=0,
            total_tokens=0,
            cost_tokens=0,
            endpoint=model.api_endpoint,
            status_code=500
        )
        db.session.add(log)
        db.session.commit()
        print(f"[API] Database committed successfully for API call")
        return jsonify({"error": f"Model request error: {str(e)}"}), 500


@api.route("/models", methods=["GET"])
def list_models():
    """List available models."""
    api_key_obj, error = verify_api_key()
    if error:
        return jsonify({"error": error}), 401
    
    models = ModelInfo.query.filter_by(is_active=True).all()
    model_list = []
    for model in models:
        model_list.append({
            "id": model.id,
            "name": model.name,
            "description": model.description,
            "max_tokens": model.max_tokens_per_request,
            "price_per_token": model.price_per_token
        })
    
    return jsonify({"data": model_list})


@api.route("/usage", methods=["GET"])
def get_usage():
    """Get user's token usage and balance."""
    api_key_obj, error = verify_api_key()
    if error:
        return jsonify({"error": error}), 401
    
    user = User.query.get(api_key_obj.user_id)
    if not user:
        return jsonify({"error": "User not found"}), 500
    
    return jsonify({
        "total_tokens": user.total_tokens,
        "used_tokens": user.used_tokens,
        "remaining_tokens": user.remaining_tokens,
        "api_key": {
            "name": api_key_obj.name,
            "total_calls": api_key_obj.total_calls,
            "total_tokens_used": api_key_obj.total_tokens_used,
            "last_used": api_key_obj.last_used.isoformat() if api_key_obj.last_used else None
        }
    })