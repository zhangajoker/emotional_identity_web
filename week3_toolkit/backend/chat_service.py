import asyncio
import json
import os
import urllib.error
import urllib.request
from collections.abc import AsyncIterator


class ChatServiceError(RuntimeError):
    pass


OLLAMA_BASE_URL = os.environ.get(
    "OLLAMA_BASE_URL",
    "http://host.docker.internal:11434",
).rstrip("/")
OLLAMA_MODEL = os.environ.get(
    "OLLAMA_MODEL",
    "qwen2.5vl:7b",
)

SYSTEM_PROMPT = """
你是“心语”，一个温和、克制的情感陪伴助手。

回复规则：
1. 先承接用户的感受，让用户知道自己的情绪被听见。
2. 尽量使用自然、简短的中文，通常不超过 180 个汉字。
3. 可以温和地提出一个问题，帮助用户继续说下去。
4. 只有合适时才给出一到两个简单可行的日常建议。
5. 不诊断疾病，不提供药物剂量，不声称替代心理咨询或医疗服务。
6. 不批评、不命令、不空洞说教，也不承诺绝对保密。
7. 如果用户提到立即伤害自己或他人的计划，优先建议联系身边可信任的人，
   拨打 120 或 110，或前往最近的急诊。
8. 不要声称自己能看见用户，也不要主动推断用户的外貌或身份。
""".strip()

CRISIS_MARKERS = (
    "不想活了",
    "活不下去了",
    "想自杀",
    "准备自杀",
    "结束生命",
    "结束自己",
    "伤害自己",
    "自残",
    "割腕",
    "跳楼",
    "吞药",
    "一了百了",
    "想死了",
    "去死算了",
    "kill myself",
    "suicide",
)

CRISIS_RESPONSE = (
    "听起来你现在可能处在很危险的时刻，我不想让你一个人面对。"
    "请先离开可能伤害自己的物品和环境，立刻联系一位可信任的人陪着你，"
    "并拨打 120 或 110，或直接前往最近的急诊。"
    "如果你已经伤害了自己，请马上拨打急救电话。"
    "你现在安全吗？身边有没有人可以陪你？"
)


def detect_crisis(content: str) -> bool:
    normalized = content.lower()
    return any(marker in normalized for marker in CRISIS_MARKERS)


def _open_chat_response(payload: dict):
    request = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/chat",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        return urllib.request.urlopen(request, timeout=180)
    except urllib.error.HTTPError as exc:
        detail = exc.read(500).decode("utf-8", errors="replace")
        raise ChatServiceError(
            f"本地模型返回 {exc.code}: {detail}"
        ) from exc
    except OSError as exc:
        raise ChatServiceError("无法连接本地情感模型") from exc


async def stream_chat(
    messages: list[dict[str, str]],
) -> AsyncIterator[str]:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": True,
        "keep_alive": "30m",
        "messages": [
            {
                "role": "system",
                "content": SYSTEM_PROMPT,
            },
            *messages,
        ],
        "options": {
            "temperature": 0.7,
            "top_p": 0.85,
            "num_predict": 300,
            "num_ctx": 4096,
        },
    }

    response = await asyncio.to_thread(
        _open_chat_response,
        payload,
    )

    try:
        while True:
            line = await asyncio.to_thread(response.readline)
            if not line:
                break

            try:
                data = json.loads(line.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError):
                continue

            if data.get("error"):
                raise ChatServiceError(str(data["error"]))

            content = data.get("message", {}).get("content", "")
            if content:
                yield content

            if data.get("done"):
                break
    except OSError as exc:
        raise ChatServiceError("情感模型连接中断") from exc
    finally:
        response.close()


def warm_up_chat_model() -> None:
    payload = {
        "model": OLLAMA_MODEL,
        "stream": False,
        "keep_alive": "30m",
        "messages": [
            {
                "role": "user",
                "content": "Reply with OK.",
            }
        ],
        "options": {
            "num_predict": 1,
            "num_ctx": 512,
        },
    }

    try:
        response = _open_chat_response(payload)
        response.read(2048)
        response.close()
        print("✅ 情感聊天模型预热完成")
    except Exception as exc:
        print(f"⚠️ 情感聊天模型预热失败: {exc}")
