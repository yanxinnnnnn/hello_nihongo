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

        grammar_lines = []
        grammar_mode = False
        section = None  # 记录当前正在处理的部分

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
                logger.debug('[process_translation] 进入循环之前')

                async for line in response.aiter_lines():
                    line = line.strip()
                    logger.debug(f'[process_translation] 进入循环，line: {line}')
                    if not line or not line.startswith("data:"):
                        continue  # 过滤无效行

                    try:
                        # **解析 JSON 数据**
                        json_data = json.loads(line[5:].strip())  # 去掉 "data: " 部分
                        delta_content = json_data.get("choices", [{}])[0].get("delta", {}).get("content", "")

                        if not delta_content:
                            continue  # 跳过空数据

                        # **结构化解析**
                        if delta_content.startswith("1. 翻译结果:"):
                            section = "translated"
                            result["translated"] = delta_content.replace("1. 翻译结果:", "").strip()
                        elif delta_content.startswith("2. 平假名注释:"):
                            section = "furigana"
                            result["furigana"] = delta_content.replace("2. 平假名注释:", "").strip()
                        elif delta_content.startswith("3. 语法解析:"):
                            section = "grammar"
                            grammar_mode = True
                        elif grammar_mode:
                            if delta_content.startswith("   ") or delta_content.startswith("\t"):
                                grammar_lines.append(delta_content.strip())
                            else:
                                grammar_mode = False
                                section = None  # 退出语法解析模式

                        # **拼接内容**
                        if section == "translated":
                            result["translated"] += delta_content.strip()
                        elif section == "furigana":
                            result["furigana"] += delta_content.strip()
                        elif section == "grammar":
                            result["grammar"] = "\n".join(grammar_lines) if grammar_lines else ""

                        # **流式返回完整的 JSON**
                        yield f"data: {json.dumps(result, ensure_ascii=False)}\n\n"
                        await asyncio.sleep(0.05)  # 控制流速

                    except json.JSONDecodeError as e:
                        logger.error(f"JSON解析失败: {e}, line: {line}")
                        continue  # 避免解析失败影响流式处理

            except httpx.RequestError as e:
                logger.error(f'请求DeepSeek API失败：{e}')
                yield "data: {\"error\": \"请求DeepSeek API失败\"}\n\n"
            except httpx.HTTPStatusError as e:
                logger.error(f'HTTP错误：{e}')
                yield "data: {\"error\": \"HTTP错误\"}\n\n"
            except Exception as e:
                logger.error(f'未知错误：{e}')
                yield "data: {\"error\": \"未知错误\"}\n\n"

    logger.debug('[stream_generator] 准备返回')
    return StreamingResponse(stream_generator(), media_type="text/event-stream")