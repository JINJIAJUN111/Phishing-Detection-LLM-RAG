import base64
import os
import time
from openai import OpenAI

MODEL = "qwen3.5-omni-plus-2026-03-15"
BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

def to_data_url(image_path: str) -> str:
    ext = image_path.split(".")[-1].lower()
    mime = "image/png" if ext == "png" else "image/jpeg"
    b64 = base64.b64encode(open(image_path, "rb").read()).decode("utf-8")
    return f"data:{mime};base64,{b64}"

def main():
    api_key = os.getenv("DASHSCOPE_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise SystemExit("Set DASHSCOPE_API_KEY (or OPENAI_API_KEY).")

    img = os.getenv("TEST_IMAGE", r"data\screenshots\sample.png")
    client = OpenAI(api_key=api_key, base_url=BASE_URL)

    # 兼容层对多模态的字段名可能不同，这里先尝试 image_url（最常见）
    messages = [{
        "role": "user",
        "content": [
            {"type": "text", "text": "你是钓鱼网站检测器。请结合图片与文本判断该页面是否为钓鱼网站。只输出 JSON: {\"is_phish\":0|1,\"reason\":\"...\"}"},
            {"type": "image_url", "image_url": {"url": to_data_url(img)}},
            {"type": "text", "text": "补充文本证据：该页面疑似仿冒登录/银行/邮件。"},
        ],
    }]

    t0 = time.time()
    resp = client.chat.completions.create(model=MODEL, messages=messages, temperature=0)
    ms = int((time.time() - t0) * 1000)

    print("latency_ms =", ms)
    print(resp.choices[0].message.content)

if __name__ == "__main__":
    main()