import sys
import asyncio
import json
import pandas as pd
import numpy as np
import lightgbm as lgb
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

app = FastAPI(title="Kiwoom AI Quant Gateway")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

class AITradingEngine:
    def __init__(self):
        self.data_dir = Path("D:/data/stocks")
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
        df['target'] = (df['close'].shift(-5) / df['close'] - 1 >= 0.02).astype(int)
        df.replace([np.inf, -np.inf], np.nan, inplace=True)
        return df.dropna(subset=self.features + ['target'])

    def train_model(self, stk_cd: str):
        file_path = self.data_dir / stk_cd / "daily" / f"{stk_cd}_daily.parquet"
        if not file_path.exists(): return False
            
        df = pd.read_parquet(file_path)
        if len(df) < 100: return False
            
        processed_df = self.generate_features(df)
        X, y = processed_df[self.features], processed_df['target']
        
        split_idx = int(len(X) * 0.8)
        train_data = lgb.Dataset(X.iloc[:split_idx], label=y.iloc[:split_idx])
        valid_data = lgb.Dataset(X.iloc[split_idx:], label=y.iloc[split_idx:], reference=train_data)
        
        params = {'objective': 'binary', 'metric': 'auc', 'verbosity': -1, 'learning_rate': 0.05}
        self.models[stk_cd] = lgb.train(params, train_data, valid_sets=[valid_data], num_boost_round=100)
        return True

    def predict(self, stk_cd: str, live_data: pd.DataFrame) -> float:
        if stk_cd not in self.models: return 0.5
        processed_df = self.generate_features(live_data)
        if processed_df.empty: return 0.5
        return float(self.models[stk_cd].predict(processed_df[self.features].iloc[-1:])[0])

class ConnectionManager:
    def __init__(self):
        self.active_connections: list[WebSocket] = []
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            await connection.send_text(json.dumps(message))

manager = ConnectionManager()
ai_engine = AITradingEngine()

@app.on_event("startup")
async def startup_event():
    print("🤖 AI 매매 엔진 가동 준비 완료")
    target_stk = "005930" # 샘플 타겟 종목
    if ai_engine.train_model(target_stk):
        asyncio.create_task(trading_monitor_loop(target_stk))

async def trading_monitor_loop(stk_cd: str):
    while True:
        await asyncio.sleep(5) 
        file_path = Path(f"D:/data/stocks/{stk_cd}/daily/{stk_cd}_daily.parquet")
        if not file_path.exists(): continue
        df = pd.read_parquet(file_path).tail(60)
        
        prob = ai_engine.predict(stk_cd, df)
        if prob > 0.70:
            signal = {
                "event": "TRADE", "action": "BUY", "stk_cd": stk_cd,
                "price": float(df['close'].iloc[-1]), "probability": round(prob * 100, 2),
                "timestamp": datetime.now().isoformat()
            }
            await manager.broadcast(signal)
            await asyncio.sleep(60) # 중복 매수 방지 쿨타임

@app.get("/api/v1/chart/{stk_cd}")
async def get_chart_data(stk_cd: str, limit: int = 300):
    file_path = Path(f"D:/data/stocks/{stk_cd}/daily/{stk_cd}_daily.parquet")
    if not file_path.exists(): return {"data": []}
    df = pd.read_parquet(file_path).tail(limit)
    return {"stk_cd": stk_cd, "data": [{"time": row['timestamp'].strftime('%Y-%m-%d'), "open": float(row['open']), "high": float(row['high']), "low": float(row['low']), "close": float(row['close']), "value": float(row['volume'])} for _, row in df.iterrows()]}

@app.websocket("/ws/trading")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            if json.loads(data).get("action") == "KILL_SWITCH":
                print("🚨 [비상] 모바일 Kill-Switch 수신. 전량 청산 로직 실행.")
                await manager.broadcast({"event": "SYSTEM", "msg": "Kill-Switch Activated"})
    except WebSocketDisconnect:
        manager.disconnect(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)