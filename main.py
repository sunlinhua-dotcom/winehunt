import os
import sys

# 将 backend 目录加入 sys.path，让内部模块可以相互引用
backend_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend")
sys.path.insert(0, backend_dir)

try:
    from backend.main import app
except ImportError:
    # 如果直接作为包导入失败，尝试直接从 path 导入
    import main as backend_main
    app = backend_main.app

if __name__ == "__main__":
    import uvicorn
    # 获取端口，优先使用 PORT 环境变量 (Zeabur 默认)
    port = int(os.getenv("PORT", os.getenv("BACKEND_PORT", "8080")))
    print(f"Starting server on port {port}...")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
