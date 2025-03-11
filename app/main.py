from fastapi import FastAPI, HTTPException, Request, Depends, Response
from fastapi.responses import RedirectResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.request_models import SentenceInput
from app.models.database import SessionLocal, TranslationRecord
from app.services.translation import process_translation
from app.services.alipay import build_alipay_login_url, get_access_token, get_user_info
from app.services.session import create_user_session, get_user_session, delete_user_session
from traceback import format_exc
from functools import wraps
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title='日语造句能力提升应用',
    version='1.0.0',
    description='一个帮助用户进行中日双向翻译、平假名注释和语法解析的应用。'
)

app.mount('/static', StaticFiles(directory='static'), name='static')

templates = Jinja2Templates(directory='static')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def login_required(func):
    @wraps(func)
    async def wrapper(request: Request, db: Session = Depends(get_db), *args, **kwargs):
        session_id = request.cookies.get("session_id")
        if not session_id:
            return RedirectResponse("/login-prompt")

        user_session = get_user_session(db, session_id)
        if not user_session:
            return RedirectResponse("/login-prompt")

        return await func(request, db, *args, **kwargs)
    return wrapper

@app.get('/', response_class=HTMLResponse)
@login_required
async def read_index(request: Request, db: Session = Depends(get_db)):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post('/records', response_model=dict)
@login_required
async def save_translation(data: dict, db: Session = Depends(get_db)):
    try:
        record = TranslationRecord(
            original_sentence=data['original'],
            translated_sentence=data['translated'],
            furigana=data['furigana'],
            grammar=data['grammar']
        )
        db.add(record)
        db.commit()
        return {'message': '保存成功！'}
    except Exception as e:
        logger.error(f'保存到数据库失败：{format_exc()}')
        raise HTTPException(status_code=500, detail='保存失败，请稍后重试。')

@app.post('/process', response_model=dict)
@login_required
async def process_sentence(data: SentenceInput):
    sentence = data.sentence.strip()
    if not sentence:
        logger.error('输入的句子为空。')
        raise HTTPException(status_code=400, detail='输入的句子不能为空。')
    
    logger.info(f'处理输入句子：{sentence}')
    result = await process_translation(sentence)
    
    if 'error' in result:
        logger.error(f'处理失败：{result["error"]}')
        raise HTTPException(status_code=500, detail=result['error'])
    
    logger.info(f'处理成功：{result}')
    return result

@app.get('/records', response_model=dict)
@login_required
async def get_records(query: str = '', page: int = 1, limit: int = 5, db: Session = Depends(get_db)):
    try:
        query = f'%{query}%'
        records_query = db.query(TranslationRecord).filter(
            (TranslationRecord.original_sentence.like(query)) |
            (TranslationRecord.translated_sentence.like(query))
        )
        
        total_records = records_query.count()
        total_pages = (total_records + limit - 1) // limit
        
        records = records_query.offset((page - 1) * limit).limit(limit).all()
        
        return {
            'records': [
                {
                    'id': record.id,
                    'original_sentence': record.original_sentence,
                    'translated_sentence': record.translated_sentence,
                    'furigana': record.furigana,
                    'grammar': record.grammar
                }
                for record in records
            ],
            'totalPages': total_pages
        }
    except Exception as e:
        logger.error(f'查询记录失败：{format_exc()}')
        raise HTTPException(status_code=500, detail=f'查询记录失败：{str(e)}')
    
@app.delete('/records/{id}')
@login_required
async def delete_record(id: int, db: Session = Depends(get_db)):
    try:
        record = db.query(TranslationRecord).filter(TranslationRecord.id == id).first()
        if not record:
            raise HTTPException(status_code=404, detail='记录不存在')
        
        db.delete(record)
        db.commit()
        return {'message': '删除成功'}
    except Exception as e:
        logger.error(f'删除记录失败：{format_exc()}')
        raise HTTPException(status_code=500, detail=f'删除记录失败：{str(e)}')

@app.get('/alipay/login', response_class=RedirectResponse)
async def alipay_login():
    return build_alipay_login_url()

@app.get('/alipay/callback')
async def alipay_callback(auth_code: str, response: Response, db: Session = Depends(get_db)):
    try:
        access_token = get_access_token(auth_code)
        user_info = get_user_info(access_token)

        session_id = create_user_session(
            db,
            open_id=user_info.get("open_id"),
            avatar=user_info.get("avatar"),
            nick_name=user_info.get("nick_name")
        )

        response.set_cookie(
            key="session_id",
            value=session_id,
            httponly=True,
            max_age=60*60*24*7,
            path='/',
            secure=True,   # 生产环境建议开启
            samesite="Lax" # 适合大多数场景，跨域时可使用 "None"
        )
        logger.debug(f"设置 Cookie 成功: session_id={session_id}")
        response.status_code = 303  # 303 See Other，防止表单重复提交
        response.headers["Location"] = "/"
        return response
    except Exception as e:
        logger.error(f'支付宝登录失败：{format_exc()}')
        raise HTTPException(status_code=500, detail=f'支付宝登录失败：{str(e)}')

@app.get('/login-prompt', response_class=HTMLResponse)
async def login_prompt():
    html_content = """
    <html>
    <head><title>登录提示</title></head>
    <body>
        <h2>您尚未登录</h2>
        <p>请点击下方按钮进行登录：</p>
        <a href="/alipay/login"><button>登录</button></a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

@app.get("/logout", response_class=RedirectResponse)
@login_required
async def logout(request: Request, response: Response, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if session_id:
        delete_user_session(db, session_id)
        response.delete_cookie("session_id")
    response.status_code = 303
    response.headers["Location"] = "/login-prompt"
    return response

@app.get("/current-user", response_model=dict)
@login_required
async def get_current_user(request: Request, db: Session = Depends(get_db)):
    session_id = request.cookies.get("session_id")
    if not session_id:
        raise HTTPException(status_code=401, detail="未登录")

    user_session = get_user_session(db, session_id)
    if not user_session:
        raise HTTPException(status_code=401, detail="会话已过期或无效")

    return {
        "open_id": user_session.open_id,
        "avatar": user_session.avatar,
        "nick_name": user_session.nick_name
    }