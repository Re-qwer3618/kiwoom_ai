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
            raise ValueError("환경 변수(.env)에 KIWOOM_APP_KEY 또는 KIWOOM_SECRET_KEY가 누락되었습니다.")

        is_mock = os.getenv("KIWOOM_MOCK_MODE", "True") == "True"
        self.base_url = "https://mockapi.kiwoom.com" if is_mock else "https://api.kiwoom.com"
        
        # 엔터프라이즈급 세션 및 재시도(Retry) 전략 설정
        self.session = requests.Session()
        retry_strategy = Retry(
            total=5,  # 최대 5회 재시도
            backoff_factor=1.0,  # 1초, 2초, 4초, 8초... 점진적 대기
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["POST", "GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)

        self._token = None
        self._expiry = 0.0
        self._last_call = 0.0
        
        # 인스턴스 기동 시 최초 1회 토큰 강제 발급 (Fail-Fast)
        self._authenticate()

    def _authenticate(self):
        """au10001: 접근토큰 발급 (실패 시 즉시 예외 발생)"""
        url = f"{self.base_url}/oauth2/token"
        payload = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "secretkey": self.secret_key
        }
        headers = {"Content-Type": "application/json;charset=UTF-8"}
        
        print("[System] 키움증권 OAuth 인증 서버에 토큰 발급을 요청합니다...")
        response = self.session.post(url, json=payload, headers=headers)
        
        if response.status_code != 200:
            raise ConnectionError(f"토큰 발급 실패 (HTTP {response.status_code}): {response.text}")
            
        data = response.json()
        if "token" not in data:
            raise KeyError(f"응답 데이터에 'token' 키가 없습니다. 응답값: {data}")

        self._token = data["token"]
        self._expiry = time.time() + 86400  # 24시간 유효
        print("[System] ✅ 접근 토큰 발급 완료.")

    def get_token(self) -> str:
        if time.time() >= (self._expiry - 300):
            self._authenticate()
        return self._token

    def request(self, tr_id: str, endpoint: str, body: Dict[str, Any]) -> dict:
        """비즈니스 TR 공통 호출기 (Rate Limit 보장)"""
        elapsed = time.time() - self._last_call
        if elapsed < 0.25:  # 초당 4회 제한 준수
            time.sleep(0.25 - elapsed)
        self._last_call = time.time()

        headers = {
            "Content-Type": "application/json;charset=UTF-8",
            "authorization": f"Bearer {self.get_token()}",
            "api-id": tr_id
        }
        
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.post(url, json=body, headers=headers)
            response.raise_for_status()
            return {"status": 200, "data": response.json()}
        except requests.exceptions.RequestException as e:
            print(f"\n[API Error] TR: {tr_id} 호출 실패 | URL: {url} | Body: {body}")
            print(f"Exception: {str(e)}")
            if e.response is not None:
                print(f"Response: {e.response.text}")
            return {"status": getattr(e.response, 'status_code', 500), "data": {}}