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
    print("🚀 Kiwoom AI Quant - After-Market Batch Collector")
    print("=" * 60)
    
    client = KiwoomRESTClient()
    fetcher = AdvancedDataFetcher(client)
    
    # 1. 거시 지표(Macro Index) 수집 (KOSPI: 001, KOSDAQ: 101)
    print("\n[1] 시장 지수(KOSPI/KOSDAQ) 시계열 데이터 수집 시작...")
    fetcher.fetch_market_index_timeseries("001", "KOSPI")
    time.sleep(1.0)
    fetcher.fetch_market_index_timeseries("101", "KOSDAQ")
    time.sleep(1.0)
    
    # 2. 마스터 유니버스 갱신 및 종목 추출
    print("\n[2] 상장 종목 마스터 추출 및 필터링 진행 중...")
    universe_df = fetcher.generate_enhanced_universe()
    target_universe = universe_df[universe_df['is_tradable'] == True]
    
    # 3. 매매 대상 전 종목 일/주/월봉 수집
    print(f"\n[3] 총 {len(target_universe)}개 종목 일/주/월봉 통합 배치 수집 시작...")
    for _, row in target_universe.iterrows():
        stk_cd = row['stk_cd']
        stk_nm = row['stk_nm']
        
        try:
            fetcher.fetch_daily_timeseries(stk_cd, stk_nm)
            time.sleep(1.0) # Rate Limit 안전선
        except Exception as e:
            print(f"❌ Error fetching {stk_cd}: {e}")
            
    print("\n✅ 일일 배치 수집 파이프라인 정상 종료")

if __name__ == "__main__":
    main()