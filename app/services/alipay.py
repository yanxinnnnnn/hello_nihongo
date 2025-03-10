import time
import base64
import logging
import requests
import urllib.parse
from fastapi import HTTPException
from app.config import config
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256

logger = logging.getLogger(__name__)

def build_alipay_login_url() -> str:
    """构建支付宝授权登录的URL"""
    params = {
        'app_id': config.get('alipay.app_id'),
        'scope': 'auth_user',
        'redirect_uri': config.get('alipay.callback_uri'),
    }
    return f"{config.get('alipay.gateway')}?{urllib.parse.urlencode(params)}"

def get_access_token(auth_code: str) -> str:
    """通过授权码获取access token"""
    params = {
        'app_id': config.get('alipay.app_id'),
        'method': 'alipay.system.oauth.token',
        'format': 'JSON',
        'charset': 'utf-8',
        'sign_type': 'RSA2',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'grant_type': 'authorization_code',
        'code': auth_code,
    }
    params['sign'] = generate_sign(params, config.get('alipay.app_private_key'))
    headers = {'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8'}
    response = requests.post(config.get('alipay.api_gateway'), data=params, headers=headers)
    result = response.json()
    logger.debug(f'[get_access_token]支付宝API Gateway响应数据：{result}')
    if 'alipay_system_oauth_token_response' in result:
        return result['alipay_system_oauth_token_response']['access_token']
    else:
        raise HTTPException(status_code=400, detail='获取 access_token 失败')

def get_user_info(access_token: str) -> dict:
    """通过access token获取用户信息"""
    params = {
        'app_id': config.get('alipay.app_id'),
        'method': 'alipay.user.info.share',
        'format': 'JSON',
        'charset': 'utf-8',
        'sign_type': 'RSA2',
        'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
        'version': '1.0',
        'auth_token': access_token,
    }
    params['sign'] = generate_sign(params, config.get('alipay.app_private_key'))

    response = requests.post(config.get('alipay.api_gateway'), data=params)
    result = response.json()
    logger.debug(f'[get_user_info]支付宝API Gateway响应数据：{result}')
    if 'alipay_user_info_share_response' in result:
        data = result['alipay_user_info_share_response']
        sign = result.get('sign')
        if verify_alipay_signature(data, sign, config.get('alipay.alipay_public_key')):
            return data
        else:
            raise HTTPException(status_code=400, detail='支付宝响应签名验证失败')
    else:
        raise HTTPException(status_code=400, detail='获取用户信息失败')

def format_private_key(private_key: str) -> str:
    """为没有头尾的私钥添加 PEM 格式的标记"""
    if not private_key.startswith("-----BEGIN"):
        private_key = "-----BEGIN PRIVATE KEY-----\n" + private_key + "\n-----END PRIVATE KEY-----"
    return private_key

def generate_sign(params: dict, private_key: str) -> str:
    """使用 RSA2 (SHA256withRSA) 生成签名"""
    param_str = '&'.join(f'{k}={v}' for k, v in sorted(params.items()))
    # 加载私钥并生成签名
    key = RSA.importKey(format_private_key(private_key))
    signer = PKCS1_v1_5.new(key)
    digest = SHA256.new(param_str.encode('utf-8'))
    sign = signer.sign(digest)
    # 签名进行 base64 编码
    return base64.b64encode(sign).decode('utf-8')

def verify_alipay_signature(data: dict, sign: str, public_key: str) -> bool:
    """验证支付宝返回数据的签名"""
    unsigned_items = {k: v for k, v in data.items() if k not in ['sign', 'sign_type']}
    unsigned_string = '&'.join(f"{k}={v}" for k, v in sorted(unsigned_items.items()))

    try:
        key = RSA.importKey(base64.b64decode(public_key))
        verifier = PKCS1_v1_5.new(key)
        digest = SHA256.new(unsigned_string.encode('utf-8'))
        decoded_sign = base64.b64decode(sign)
        return verifier.verify(digest, decoded_sign)
    except Exception as e:
        print(f"签名验证失败: {e}")
        return False
