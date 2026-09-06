from fastapi import FastAPI, WebSocket
import asyncio
from src.kiwoom.client import KiwoomRestClient

app = FastAPI()
client = KiwoomRestClient()

@app.get("/api/portfolio")
async def get_portfolio():
    # 일별잔고수익률조회 (ka01690) 호출
    data = client.request_tr("ka01690", "/api/dostk/acnt", {"qry_dt": "20260906"})
    return {
        "total_profit_rate": data.get("tot_prft_rt"),
        "estimated_assets": data.get("day_stk_asst"),
        "positions": data.get("day_bal_rt", [])
    }

@app.websocket("/ws/market")
async def market_stream(websocket: WebSocket):
    await websocket.accept()
    while True:
        # Redis를 통해 수집된 실시간 틱 데이터 및 AI 시그널 전송
        await websocket.send_json({"type": "MARKET_UPDATE", "data": "..."})
        await asyncio.sleep(1)