import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_mock_parquet(stk_cd="005930", days=200):
    output_dir = "D:/data/ohlcv"
    os.makedirs(output_dir, exist_ok=True)
    
    # 200일치 가상 데이터 생성
    dates = [datetime.today() - timedelta(days=x) for x in range(days)]
    dates.reverse()
    
    # Random Walk 기반 가상 주가 생성
    np.random.seed(42)
    returns = np.random.normal(0, 0.02, days)
    price_series = 70000 * np.exp(np.cumsum(returns))
    
    df = pd.DataFrame({
        "timestamp": dates,
        "open": price_series * np.random.uniform(0.99, 1.01, days),
        "high": price_series * np.random.uniform(1.01, 1.03, days),
        "low": price_series * np.random.uniform(0.97, 0.99, days),
        "close": price_series,
        "volume": np.random.randint(1000000, 50000000, days)
    })
    
    # 데이터 정제 및 저장
    df['timestamp'] = pd.to_datetime(df['timestamp']).dt.normalize()
    file_path = f"{output_dir}/{stk_cd}.parquet"
    df.to_parquet(file_path, engine="pyarrow", compression="snappy")
    print(f"✅ Mock 데이터 생성 완료: {file_path} (이 스크립트 실행 후 차트 모니터를 새로고침하세요)")

if __name__ == "__main__":
    generate_mock_parquet("005930")