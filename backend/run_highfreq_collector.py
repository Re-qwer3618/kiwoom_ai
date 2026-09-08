import sys
import time
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

ENV_PATH = Path("D:/00-python/.env")
load_dotenv(dotenv_path=ENV_PATH, encoding="utf-8-sig")

from src.kiwoom.client import KiwoomRESTClient
from src.data.fetcher import AdvancedDataFetcher

def main():
    print("=" * 60)
    print("🚀 Kiwoom AI Quant - High-Frequency (Min/Tick) Collector")
    print("=" * 60)
    
    client = KiwoomRESTClient()
    fetcher = AdvancedDataFetcher(client)
    
    target_universe = [
        {"stk_cd": "005930", "stk_nm": "삼성전자"},
        {"stk_cd": "000660", "stk_nm": "SK하이닉스"},
        {"stk_cd": "373220", "stk_nm": "LG에너지솔루션"}
    ]
    
    for row in target_universe:
        stk_cd = row['stk_cd']
        stk_nm = row['stk_nm']
        
        try:
            # 통합된 메서드로 1분봉 및 틱 데이터 연속 수집 호출
            fetcher.fetch_minute_tick_batch(stk_cd, stk_nm, unit="minute", tick_range="1")
            fetcher.fetch_minute_tick_batch(stk_cd, stk_nm, unit="tick")
            
            time.sleep(1) # API Rate Limit 방어
            
        except Exception as e:
            print(f"❌ Error fetching {stk_cd}: {e}")
            
    print("\n✅ 고빈도 분봉/틱봉 데이터 수집 정상 종료")

if __name__ == "__main__":
    main()