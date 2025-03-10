import time
import base64
import logging
import requests
from urllib.parse import urlencode, unquote
from fastapi import HTTPException
from app.config import config
from Crypto.Signature import PKCS1_v1_5
from Crypto.PublicKey import RSA
from Crypto.Hash import SHA256
from traceback import format_exc

logger = logging.getLogger(__name__)

def build_alipay_login_url() -> str:
    """构建支付宝授权登录的URL"""
    params = {
        'app_id': config.get('alipay.app_id'),
        'scope': 'auth_user',
        'redirect_uri': config.get('alipay.callback_uri'),
    }
    return f"{config.get('alipay.gateway')}?{urlencode(params)}"

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
    # 签名进行 base64 编码
    return base64.b64encode(sign).decode('utf-8')

def format_public_key(public_key: str) -> str:
    """为没有头尾的公钥添加 PEM 格式的标记"""
    if not public_key.startswith("-----BEGIN"):
        public_key = "-----BEGIN PUBLIC KEY-----\n" + public_key + "\n-----END PUBLIC KEY-----"
    return public_key

def clean_value(value: str) -> str:
    """清理参数值中的多余空格和不可见字符"""
    if isinstance(value, str):
        # 移除首尾空白，替换连续空白为单个空格
        return ' '.join(value.strip().split())
    return str(value)

def verify_alipay_signature(data: dict, sign: str, public_key: str) -> bool:
    """验证支付宝返回数据的签名，严格按照支付宝签名规则实现"""
    # 1. 过滤掉 sign 和 sign_type 字段，并确保不包含空值的参数
    unsigned_items = {k: clean_value(v) for k, v in data.items()
                      if k not in ['sign', 'sign_type'] and v not in [None, ""]}

    # 2. 按字母顺序拼接待签名字符串
    unsigned_string = '&'.join(f"{k}={v}" for k, v in sorted(unsigned_items.items()))

    try:
        formatted_public_key = format_public_key(public_key)
        logger.debug(f"[verify_alipay_signature] 格式化后的公钥: {formatted_public_key}")
        logger.debug(f"[verify_alipay_signature] 生成的待签名字符串: {unsigned_string}")

        key = RSA.importKey(formatted_public_key)
        verifier = PKCS1_v1_5.new(key)
        digest = SHA256.new(unsigned_string.encode('utf-8'))

        # 解码签名（注意：支付宝的签名通常是 Base64 编码的）
        decoded_sign = base64.b64decode(unquote(sign))

        if verifier.verify(digest, decoded_sign):
            logger.debug("[verify_alipay_signature] 签名验证成功")
            return True
        else:
            logger.error(f"[verify_alipay_signature] 签名验证失败: 原始字符串={unsigned_string}, 签名={sign}")
            return False

    except Exception as e:
        logger.error(f"[verify_alipay_signature] 签名验证异常: {format_exc()}")
        return False
