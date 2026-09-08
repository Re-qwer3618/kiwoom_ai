import os
import json
from typing import Dict
from src.kiwoom.client import KiwoomRESTClient

class KiwoomOrderManager:
    def __init__(self, client: KiwoomRESTClient):
        self.client = client
        self.account_no = os.getenv("KIWOOM_ACCOUNT_NO") # .env에 8자리 계좌번호 세팅 필요
        
        if not self.account_no:
            raise ValueError("[Error] .env 파일에 KIWOOM_ACCOUNT_NO가 설정되지 않았습니다.")

    def execute_order(self, stk_cd: str, order_type: str, qty: int, price: int) -> Dict:
        """
        키움증권 REST API 기반 국내주식 주문 실행 (OPEN API 완전 배제)
        order_type: 'BUY' (신규매수), 'SELL' (신규매도)
        """
        print(f"⚡ [Order Execution] {order_type} | 종목: {stk_cd} | 수량: {qty} | 단가: {price}")
        
        # 키움 REST API 주문 코드 매핑 (실제 명세서 기준 설정 필요)
        # 예: 1: 신규매수, 2: 신규매도
        trade_type = "1" if order_type == "BUY" else "2"
        
        payload = {
            "acnt_no": self.account_no,     # 계좌번호
            "pdno": stk_cd,                 # 종목코드
            "ord_qty": str(qty),            # 주문수량
            "ord_unpr": str(price),         # 주문단가 (지정가 기준)
            "ord_dvsn": "00",               # 주문구분 (00: 지정가, 03: 시장가)
            "ord_type": trade_type          # 매수/매도 구분
        }
        
        # 가상의 주문 TR 코드 (실제 주문 API 엔드포인트 명세 참조)
        res = self.client.request(
            tr_id="ttc803600", 
            endpoint="/api/order/domestic", 
            body=payload
        )
        
        if res["status"] == 200:
            order_no = res["data"].get("odno", "UNKNOWN")
            print(f"✅ [주문 성공] 접수번호: {order_no}")
            return {"status": "SUCCESS", "order_no": order_no}
        else:
            print(f"❌ [주문 실패] {res.get('data')}")
            return {"status": "FAILED", "reason": res.get("data")}