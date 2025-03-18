import httpx
import logging
from urllib.parse import urljoin
from app.config import config
from fastapi.responses import StreamingResponse
import asyncio
import json

logger = logging.getLogger(__name__)

async def process_translation(sentence: str):
    logger.debug('[process_translation] 进入函数')
    base_url = config.get('deepseek.base_url', "https://api.deepseek.com")
    chat_api = config.get('deepseek.chat_api', '/chat/completions')
    api_key = config.get('deepseek.api_key', '')
    timeout = config.get('deepseek.timeout', 10)
    api_url = urljoin(base_url, chat_api)

    if not api_key:
        logger.error('DeepSeek API Key未配置，请在配置文件中提供有效的值。')
        async def error_stream():
            yield "data: {\"error\": \"DeepSeek API Key未配置\"}\n\n"
        return StreamingResponse(error_stream(), media_type="text/event-stream")

    messages = [
        {
            'role': 'system',
            'content': (
                '你是一个帮助用户进行中日翻译的助手。当用户输入中文时，'
                '请将其翻译为日语，并提供以下格式的输出：\n'
                '1. 翻译结果: [翻译后的日语句子]\n'
                '2. 平假名注释: [日语句子的平假名形式]\n'
                '3. 语法解析: [简单的语法分析和关键点]\n'
                '当用户输入日语时，请提供句子的平假名注释、语法解析，'
                '并翻译为中文，保持同样的格式输出。'
            )
        },
        {'role': 'user', 'content': sentence}
    ]

    payload = {
        'model': 'deepseek-chat',
        'messages': messages,
        'stream': True  # 开启流式模式
    }
    logger.debug('[process_translation] 请求参数构造完成')

    async def stream_generator():
        logger.debug('[process_translation] 进入stream_generator')
        result = {
            'original': sentence,
            'translated': '',
            'furigana': '',
            'grammar': '',
        }

        buffer = ''
        section = None

        async with httpx.AsyncClient(timeout=timeout) as client:
            try:
                logger.debug(f'DeepSeek API请求payload：{payload}')
                response = await client.post(
                    api_url,
                    json=payload,
                    headers={
                        'Authorization': f'Bearer {api_key}',
                        'Content-Type': 'application/json',
                        'Accept': 'application/json'
                    },
                    timeout=timeout
                )
                response.raise_for_status()

                async for line in response.aiter_lines():
                    line = line.strip()
                    if not line:
                        continue

                    if line == "data: [DONE]":
                        logger.debug("[process_translation] 流式数据接收完毕")
                        break

                    try:
                        json_data = json.loads(line[5:].strip())
                        delta_content = json_data.get("choices", [{}])[0].get("delta", {}).get("content")

                        if delta_content is None:
                            continue

                        logger.debug(f"接收到的内容: {delta_content}")
                        buffer += delta_content
                        logger.debug(f'buffer: {buffer}')

                        if "1. 翻译结果:" in buffer:
                            section = "translated"
                        if "2. 平假名注释:" in buffer:
                            section = "furigana"
                        if "3. 语法解析:" in buffer:
                            section = "grammar"

                        if section == "translated":
                            result["translated"] = buffer.replace('1. 翻译结果:', '').strip()
                        elif section == "furigana":
                            if '2. 平假名注释' in result["translated"]:
                                result["translated"] = result["translated"].replace('2. 平假名注释', '').strip()
                            if buffer.endswith('2. 平假名注释:'):
                                buffer = buffer.split('2. 平假名注释:')[1].strip()
                            result["furigana"] = buffer.strip()
                        elif section == "grammar":
                            if '3. 语法解析' in result["furigana"]:
                                result["furigana"] = result["furigana"].replace('3. 语法解析', '').strip()
                            if buffer.endswith('3. 语法解析:'):
                                buffer = buffer.split('3. 语法解析:')[1].strip()
                            result["grammar"] = buffer.strip()
                        
                        logger.debug(f'result: {result}')

                        yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.05)

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}, line: {line}")
                        continue

            except Exception as e:
                logger.error(f'未知错误：{e}')
                yield "data: {\"error\": \"未知错误\"}\n\n"

    logger.debug('[stream_generator] 准备返回')
    return StreamingResponse(stream_generator(), media_type="text/event-stream")