from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from app.models.request_models import SentenceInput
from app.models.database import SessionLocal, TranslationRecord
from app.services.translation import process_translation
from app.services.alipay import build_alipay_login_url, get_access_token, get_user_info
from traceback import format_exc
import logging

logger = logging.getLogger(__name__)

app = FastAPI(
    title='日语造句能力提升应用',
    version='1.0.0',
    description='一个帮助用户进行中日双向翻译、平假名注释和语法解析的应用。'
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=['*'],
    allow_headers=['*'],
)

app.mount('/static', StaticFiles(directory='static'), name='static')

templates = Jinja2Templates(directory='static')

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get('/', response_class=HTMLResponse)
async def read_index(request: Request):
    return templates.TemplateResponse('index.html', {'request': request})

@app.post('/records', response_model=dict)
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
async def alipay_callback(auth_code: str):
    try:
        access_token = get_access_token(auth_code)
        user_info = get_user_info(access_token)
        return user_info
    except Exception as e:
        logger.error(f'支付宝登录失败：{format_exc()}')
        raise HTTPException(status_code=500, detail=f'支付宝登录失败：{str(e)}')