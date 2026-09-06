import os
from pathlib import Path

def create_clean_env():
    env_path = Path("D:/00-python/.env")
    env_path.parent.mkdir(parents=True, exist_ok=True)
    
    # 실제 발급받은 키움 REST API 키 입력
    app_key = "LsnCsEyFtHEFAsUIpK3dEMBry7wklt3BbF-6UIPpASw"
    secret_key = "f4b_CeiuGppPL0z5yFKcU_n1BhNrPcW_Rq1v4sxX26w"
    
    env_content = f"""KIWOOM_APP_KEY={app_key}
KIWOOM_SECRET_KEY={secret_key}
KIWOOM_MOCK_MODE=True
"""
    # BOM 없는 순수 UTF-8로 파일 강제 작성
    with open(env_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(env_content)
        
    print(f"✅ {env_path} 파일이 완벽한 포맷으로 생성되었습니다.")

if __name__ == "__main__":
    create_clean_env()