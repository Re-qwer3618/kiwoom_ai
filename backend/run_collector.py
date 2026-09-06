import sys
import os
from pathlib import Path
from dotenv import load_dotenv

# 백엔드 최상위 디렉토리를 Python Path에 추가
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

# 환경 변수 명시적 로드 및 상태 검증
ENV_PATH = Path("D:/00-python/.env")
print(f"[System] 환경 변수 경로 확인: {ENV_PATH} (존재 여부: {ENV_PATH.exists()})")

# --- 디버그: .env 원본 내용 직접 확인 ---
try:
    with open(ENV_PATH, "r", encoding="utf-8") as f:
        raw_content = f.read()
    print("[Debug] .env 원본 내용 (repr):")
    print(repr(raw_content))
except UnicodeDecodeError as e:
    print(f"[Debug] UTF-8 디코딩 실패: {e}")
    with open(ENV_PATH, "rb") as f:
        raw_bytes = f.read()
    print(f"[Debug] 원본 바이트: {raw_bytes[:200]}")

# --- load_dotenv 호출 + 반환값 확인 ---
loaded = load_dotenv(dotenv_path=ENV_PATH, override=True, verbose=True)
print(f"[Debug] dotenv 로드 성공 여부: {loaded}")

app_key = os.getenv("KIWOOM_APP_KEY")
secret_key = os.getenv("KIWOOM_SECRET_KEY")

print(f"[Debug] os.getenv 결과 -> APP_KEY: {repr(app_key)}, SECRET_KEY: {repr(secret_key)}")

if not app_key or not secret_key:
    print("❌ [치명적 오류] .env 파일을 찾았으나 키값이 비어있거나 읽을 수 없습니다.")
    sys.exit(1)
else:
    print(f"✅ 환경 변수 로드 성공 (APP_KEY: {app_key[:5]}... / SECRET_KEY: {secret_key[:5]}...)")

from src.kiwoom.client import KiwoomRESTClient
from src.data.fetcher import DataFetcher

def main():
    print("=" * 60)
    print("🚀 System Booting: Kiwoom REST API Collector")
    print("=" * 60)
    
    # API 클라이언트 초기화
    client = KiwoomRESTClient()
    fetcher = DataFetcher(client)
    
    print("\n[Step 1] 전 종목 유니버스 갱신 중...")
    universe_df = fetcher.generate_universe()
    print(f"Total Tickers: {len(universe_df)}")
    
    print("\n[Step 2] OHLCV 시계열 데이터 수집 시작...")
    test_universe = universe_df.head(5) 
    
    for _, row in test_universe.iterrows():
        try:
            fetcher.fetch_ohlcv(row['stk_cd'], row['stk_nm'])
        except Exception as e:
            print(f"❌ Error fetching {row['stk_cd']}: {str(e)}")
            
    print("\n✅ 데이터 수집 파이프라인 정상 종료")

if __name__ == "__main__":
    main()