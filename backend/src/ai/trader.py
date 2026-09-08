import pandas as pd
import numpy as np
import lightgbm as lgb
from datetime import datetime
from src.kiwoom.client import KiwoomRESTClient

class AITradingEngine:
    def __init__(self, client: KiwoomRESTClient):
        self.client = client
        self.models = {}
        self.features = ['ret_1d', 'ret_5d', 'disp_5', 'disp_20', 'vol_ratio']

    def generate_features(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.copy()
        df.sort_values('timestamp', inplace=True)
        df['ret_1d'] = df['close'].pct_change(1)
        df['ret_5d'] = df['close'].pct_change(5)
        df['ma_5'] = df['close'].rolling(5).mean()
        df['ma_20'] = df['close'].rolling(20).mean()
        df['disp_5'] = df['close'] / df['ma_5'] - 1
        df['disp_20'] = df['close'] / df['ma_20'] - 1
        df['vol_ma_20'] = df['volume'].rolling(20).mean()
        df['vol_ratio'] = df['volume'] / (df['vol_ma_20'] + 1e-8)
        
        # 5봉 뒤 2% 이상 상승 여부를 타겟으로 설정
        df['target'] = (df['close'].shift(-5) / df['close'] - 1 >= 0.02).astype(int)
        return df.dropna(subset=self.features + ['target'])

    def execute_live_trading(self, stk_cd: str, live_df: pd.DataFrame):
        """실시간 데이터 추론 후 75% 승률 이상 시 실제 주문 실행"""
        if stk_cd not in self.models:
            print(f"[{stk_cd}] 학습된 AI 모델이 없습니다.")
            return None
            
        processed = self.generate_features(live_df)
        if processed.empty: return None
        
        # LightGBM 상승 확률 예측
        latest_features = processed[self.features].iloc[-1:]
        buy_prob = float(self.models[stk_cd].predict(latest_features)[0])
        
        if buy_prob >= 0.75:
            current_price = float(live_df['close'].iloc[-1])
            qty = 10 # 켈리 배팅 적용 로직 대체 (테스트용 고정 수량)
            
            # 실제 키움 REST API 주문 실행 (매수)
            payload = {
                "acnt_no": "계좌번호8자리", "pdno": stk_cd, 
                "ord_qty": str(qty), "ord_unpr": str(current_price), 
                "ord_dvsn": "00", "ord_type": "1" # 1: 신규매수
            }
            # 실제 주문 시 아래 주석 해제 (모의투자 API 활용)
            # res = self.client.request(tr_id="ttc803600", endpoint="/api/order/domestic", body=payload)
            
            signal = {
                "event": "TRADE", "action": "BUY", "stk_cd": stk_cd,
                "price": current_price, "probability": round(buy_prob * 100, 1),
                "timestamp": datetime.now().isoformat()
            }
            return signal
        return None