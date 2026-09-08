import os
import time
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from typing import Dict, Any

class KiwoomRESTClient:
    def __init__(self):
        self.app_key = os.getenv("KIWOOM_APP_KEY")
        self.secret_key = os.getenv("KIWOOM_SECRET_KEY")
        
        if not self.app_key or not self.secret_key:
            raise ValueError("[Error] .env 파일에 API 키가 설정되지 않았습니다.")

        is_mock = os.getenv("KIWOOM_MOCK_MODE", "True") == "True"
        self.base_url = "https://mockapi.kiwoom.com" if is_mock else "https://api.kiwoom.com"
        
        self.session = requests.Session()
        # 기초적인 네트워크 에러 방어
        retry_strategy = Retry(total=3, backoff_factor=1.0, status_forcelist=[500, 502, 503, 504])
        self.session.mount("https://", HTTPAdapter(max_retries=retry_strategy))

        self._token = None
        self._expiry = 0.0
        self._last_call = 0.0
        
        self._authenticate()

    def _authenticate(self):
        url = f"{self.base_url}/oauth2/token"
        payload = {"grant_type": "client_credentials", "appkey": self.app_key, "secretkey": self.secret_key}
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        
        response = self.session.post(url, json=payload, headers=headers)
        if response.status_code != 200:
            raise ConnectionError(f"인증 실패: {response.text}")
            
        self._token = response.json()["token"]
        self._expiry = time.time() + 86400  
        print("✅ 키움증권 REST API 접근토큰 발급 완료")

    def get_token(self) -> str:
        if time.time() >= (self._expiry - 300):
            self._authenticate()
        return self._token

    def request(self, tr_id: str, endpoint: str, body: Dict[str, Any], cont_yn: str = "", next_key: str = "") -> dict:
        """API Rate Limit 방어 및 HTTP 429 지수 백오프(Exponential Backoff) 재시도 로직 적용"""
        max_retries = 4
        
        for attempt in range(max_retries):
            # 모의투자 환경을 고려하여 기본 딜레이를 0.5초로 보수적 확장
            elapsed = time.time() - self._last_call
            if elapsed < 0.5:
                time.sleep(0.5 - elapsed)
            
            self._last_call = time.time()

            headers = {
                "Content-Type": "application/json;charset=UTF-8",
                "authorization": f"Bearer {self.get_token()}",
                "api-id": tr_id
            }
            if cont_yn: headers["cont-yn"] = cont_yn
            if next_key: headers["next-key"] = next_key
            
            url = f"{self.base_url}{endpoint}"
            
            try:
                response = self.session.post(url, json=body, headers=headers)
                
                if response.status_code == 200:
                    return {"status": 200, "data": response.json(), "header": dict(response.headers)}
                
                elif response.status_code == 429:
                    # 429 에러 발생 시: 2초, 4초, 8초로 대기 시간을 기하급수적으로 늘림
                    wait_time = 2 ** (attempt + 1)
                    print(f"⚠️ [Rate Limit] 서버 유량 통제 감지. {wait_time}초 대기 후 재시도... ({attempt+1}/{max_retries})")
                    time.sleep(wait_time)
                    continue
                    
                else:
                    print(f"❌ [TR: {tr_id}] API Error: HTTP {response.status_code} | {response.text}")
                    return {"status": response.status_code, "data": {}, "header": {}}
                    
            except Exception as e:
                print(f"❌ Network Error: {e}")
                time.sleep(2)
                continue
                
        return {"status": 500, "data": {}, "header": {}}