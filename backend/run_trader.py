import sys
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import lightgbm as lgb

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

ENV_PATH = Path("D:/00-python/.env")
load_dotenv(dotenv_path=ENV_PATH, encoding="utf-8-sig")

from src.kiwoom.client import KiwoomRESTClient
from src.ai.features import FeatureEngineer

class AITradingDaemon:
    def __init__(self):
        self.client = KiwoomRESTClient()
        self.models = {}
        self.data_dir = Path("D:/data/stocks")
        self.features = ['ret_1d', 'ret_5d', 'disp_5', 'disp_20', 'vol_ratio']
        
    def train_or_load_model(self, stk_cd: str):
        """저장된 Parquet 데이터를 읽어 LightGBM 모델 훈련"""
        file_path = self.data_dir / stk_cd / "daily" / f"{stk_cd}_daily.parquet"
        if not file_path.exists():
            return False
            
        df = pd.read_parquet(file_path)
        processed_df = FeatureEngineer.create_features(df)
        
        if len(processed_df) < 100:  # 데이터 부족 시 훈련 스킵
            return False
            
        X = processed_df[self.features]
        y = processed_df['target']
        
        train_data = lgb.Dataset(X, label=y)
        params = {'objective': 'binary', 'metric': 'auc', 'verbosity': -1}
        
        # 모델 훈련 후 메모리에 캐싱
        self.models[stk_cd] = lgb.train(params, train_data, num_boost_round=100)
        return True

    def scan_and_trade(self, stk_cd: str):
        """실시간 매매 판단"""
        if stk_cd not in self.models:
            if not self.train_or_load_model(stk_cd):
                return
                
        # 1. 최우선 호가 조회 (ka10004)
        depth_res = self.client.request("ka10004", "/api/dostk/mrkcond", {"stk_cd": stk_cd})
        if depth_res["status"] != 200 or not depth_res["data"]:
            return
            
        ask_price = float(str(depth_res["data"].get("sel_fpr_bid", 0)).replace('+', '').replace('-', ''))
        
        if ask_price <= 0:
            return

        # 2. 계좌 잔고 확인 (ka01690)
        today = pd.Timestamp.now().strftime("%Y%m%d")
        acc_res = self.client.request("ka01690", "/api/dostk/acnt", {"qry_dt": today})
        balance = float(acc_res["data"].get("dbst_bal", 0)) if acc_res["status"] == 200 else 0

        # 3. 실시간 피처 벡터 생성 (마지막 종가 데이터를 활용)
        file_path = self.data_dir / stk_cd / "daily" / f"{stk_cd}_daily.parquet"
        df = pd.read_parquet(file_path).tail(30)
        live_features = FeatureEngineer.create_features(df).iloc[-1:][self.features]
        
        # 4. AI 추론
        buy_prob = self.models[stk_cd].predict(live_features)[0]
        
        # 5. 리스크 기반 매매 집행 (하프 켈리)
        if buy_prob > 0.70 and balance > ask_price * 10:
            max_inv = balance * 0.05  # 최대 5% 투자
            qty = int(max_inv // ask_price)
            print(f"🚀 [BUY] {stk_cd} | 단가: {ask_price} | 수량: {qty} | AI확률: {buy_prob*100:.1f}%")
            # 향후 실제 주문 API 호출 로직 연결
        elif buy_prob < 0.30:
            print(f"📉 [SELL] {stk_cd} | AI확률: {buy_prob*100:.1f}% (보유 시 청산)")

def main():
    print("=" * 60)
    print("🤖 Kiwoom AI Auto-Trading Engine Booting...")
    print("=" * 60)
    
    daemon = AITradingDaemon()
    
    # 장중 실시간 처리를 위한 매매 타겟 유니버스 (수십 종목으로 제한)
    # 명세서 원칙: 전종목 시세는 폴링하지 않고 관심종목만 순회
    target_universe = ["005930", "000660", "373220"] 
    
    for code in target_universe:
        daemon.train_or_load_model(code)
        
    print("\n✅ AI 모델 훈련 완료. 장중 실시간 감시를 시작합니다.\n")
    
    while True:
        for code in target_universe:
            daemon.scan_and_trade(code)
        time.sleep(1)  # 초당 API 호출 한도 통제

if __name__ == "__main__":
    main()