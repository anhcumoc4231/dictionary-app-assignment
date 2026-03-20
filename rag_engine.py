"""
rag_engine.py — Retrieval-Augmented Generation cho Từ điển
===========================================================
Sử dụng Google Gemini API để tóm tắt nghĩa thuần túy và 
giải thích ngữ cảnh sử dụng dựa trên dữ liệu thô (Retrieval).
"""

import os
import google.generativeai as genai  # type: ignore
from typing import Optional

def setup_api_key(api_key: str) -> None:
    """Cấu hình Gemini API Key."""
    genai.configure(api_key=api_key)

def check_has_key() -> bool:
    """Kiểm tra xem API Key đã được cấu hình chưa."""
    # Tự động gán key tĩnh của user nếu chưa có
    if not os.environ.get("GEMINI_API_KEY"):
        key = "AIzaSyA6VHUyK2gtsAgzsFPZo39ZuvyoZ96kjxk"
        os.environ["GEMINI_API_KEY"] = key
        # Cấu hình ngay cho thư viện genai
        setup_api_key(key)
    return bool(os.environ.get("GEMINI_API_KEY"))

def setup_from_env() -> bool:
    """Cấu hình từ biến môi trường (nếu có)."""
    key = os.environ.get("GEMINI_API_KEY")
    if key:
        setup_api_key(key)
        return True
    return False

def summarize_definition(word: str, raw_text: str) -> str:
    """
    Sử dụng AI để phân tích dữ liệu từ điển thô và trả về nghĩa thuần túy.
    """
    
    prompt = f"""Bạn là một từ điển Anh-Việt thông minh. 
Dữ liệu thô từ cuốn từ điển cũ cho từ "{word}":
{raw_text}

NHIỆM VỤ CỦA BẠN:
Trích xuất và tóm tắt thành 2 phần cực kỳ ngắn gọn, hiện đại theo format sau:

1. Nghĩa tiếng Việt: (Chỉ 1-2 nghĩa phổ biến nhất hiện nay, cực kỳ ngắn gọn)
2. English Context (Ngữ cảnh tiếng Anh): (Cho 1-2 câu ví dụ ngắn bằng tiếng Anh có chứa từ này, và giải thích nhanh cách dùng bằng tiếng Anh hoặc tiếng Việt).

Giọng văn chuyên nghiệp, đi thẳng vào vấn đề. KHÔNG dài dòng.
"""

    models_to_try = [
        'gemini-2.5-flash',
        'gemini-2.0-flash',
        'gemini-1.5-flash',
        'gemini-1.5-pro',
        'gemini-1.0-pro',
        'gemini-pro'
    ]

    last_error = ""
    for model_name in models_to_try:
        try:
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(prompt)
            # If successful, return and we are done
            return f"{response.text}\n\n[Powered by: {model_name}]"
        except Exception as e:
            if "404" in str(e) or "403" in str(e):
                last_error = str(e)
                continue # Try next model
            # For other errors (like network/quota), fail fast
            return f" Lỗi kết nối AI khi gọi model {model_name}: {str(e)}\n\nVui lòng kiểm tra lại kết nối mạng hoặc API Key."
            
    # Nếu chạy hết danh sách mà vẫn lỗi 404, thử query list models để report log
    available_models = []
    try:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
    except Exception:
        pass
    
    debug_info = f"Các model bạn có quyền: {', '.join(available_models)}" if available_models else "Không tìm thấy model nào."
    
    return f" Lỗi AI (Fallback đã cạn): {last_error}\n\nAPI Key của bạn không có quyền truy cập vào các model phổ biến.\n{debug_info}\nVui lòng tạo key mới tại Google AI Studio."
