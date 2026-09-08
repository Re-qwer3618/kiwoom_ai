import pandas as pd
import numpy as np

class FeatureEngineer:
    @staticmethod
    def create_features(df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        if 'timestamp' in df.columns:
            df.sort_values('timestamp', inplace=True)
            
        # 1. 가격 모멘텀 (Price Momentum)
        df['ret_1d'] = df['close'].pct_change(1)
        df['ret_5d'] = df['close'].pct_change(5)
        
        # 2. 이동평균선 이격도 (Moving Average Disparity)
        df['ma_5'] = df['close'].rolling(5).mean()
        df['ma_20'] = df['close'].rolling(20).mean()
        df['disp_5'] = df['close'] / df['ma_5'] - 1
        df['disp_20'] = df['close'] / df['ma_20'] - 1
        
        # 3. 거래량 회전 및 모멘텀 (Volume Dynamics)
        df['vol_ma_20'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / (df['vol_ma_20'] + 1e-8)
        
        # 4. 타겟 변수 (Target Y): 5봉 뒤 종가가 현재가 대비 3% 이상 상승했는가?
        df['future_ret_5d'] = df['close'].shift(-5) / df['close'] - 1
        df['target'] = (df['future_ret_5d'] >= 0.03).astype(int)
        
        feature_cols = ['ret_1d', 'ret_5d', 'disp_5', 'disp_20', 'vol_ratio']
        df = df.replace([np.inf, -np.inf], np.nan).dropna(subset=feature_cols + ['target'])
        
        return df[['close', 'target'] + feature_cols]