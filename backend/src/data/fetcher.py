import os
import pandas as pd
import FinanceDataReader as fdr
from pathlib import Path
from datetime import datetime
from src.kiwoom.client import KiwoomRESTClient

class AdvancedDataFetcher:
    def __init__(self, client: KiwoomRESTClient):
        self.client = client
        self.base_dir = Path("D:/data")
        
        self.universe_dir = self.base_dir / "universe"
        self.stocks_dir = self.base_dir / "stocks"
        
        self.universe_dir.mkdir(parents=True, exist_ok=True)
        self.stocks_dir.mkdir(parents=True, exist_ok=True)

    def _upsert_parquet(self, new_df: pd.DataFrame, file_path: Path):
        """기존 파일과 병합 후 timestamp 기준 중복 제거 (최신 데이터 유지)"""
        if file_path.exists():
            try:
                existing_df = pd.read_parquet(file_path)
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                combined_df.sort_values('timestamp', inplace=True)
                combined_df.drop_duplicates(subset=['timestamp'], keep='last', inplace=True)
                combined_df.to_parquet(file_path, engine="pyarrow", compression="snappy")
            except Exception as e:
                print(f"[Error] Parquet 병합 실패 ({file_path}): {e}")
        else:
            file_path.parent.mkdir(parents=True, exist_ok=True)
            new_df.sort_values('timestamp', inplace=True)
            new_df.to_parquet(file_path, engine="pyarrow", compression="snappy")

    def generate_enhanced_universe(self) -> pd.DataFrame:
        """코스피/코스닥 상장 마스터 수집 및 is_tradable(우선주/ETF 제외) 플래그 처리"""
        print("[1] 상장 종목 마스터 추출 및 필터링 진행 중...")
        
        # KRX-DESC는 상장일, 업종, 대표자명 등 상세 메타데이터 반환
        df_krx = fdr.StockListing('KRX-DESC')
        
        # [Patch] FinanceDataReader의 원본 컬럼명('Code')을 정확히 'stk_cd'로 매핑
        df_krx.rename(columns={'Code': 'stk_cd', 'Name': 'stk_nm', 'Sector': 'sector'}, inplace=True)
        
        # 동적 스키마 방어 로직 (버전에 따라 Market 컬럼이 없을 경우 대비)
        base_cols = ['stk_cd', 'stk_nm', 'sector']
        if 'Market' in df_krx.columns:
            base_cols.append('Market')
            
        # 업종(sector)이 없는 종목 제외 후 복사본 생성
        df_master = df_krx[base_cols].dropna(subset=['sector']).copy()
        
        def check_tradable(row):
            name = str(row['stk_nm'])
            if name.endswith('우') or name.endswith('우B') or name.endswith('우(전환)'): return False
            if '스팩' in name or 'SPAC' in name.upper(): return False
            if '리츠' in name or 'REIT' in name.upper(): return False
            if name.endswith('ETN') or name.endswith('ETF'): return False
            return True

        df_master['is_tradable'] = df_master.apply(check_tradable, axis=1)
        
        today_str = datetime.today().strftime("%Y%m%d")
        history_path = self.universe_dir / "stock_master_history" / f"stock_master_{today_str}.parquet"
        history_path.parent.mkdir(parents=True, exist_ok=True)
        
        df_master.to_parquet(self.universe_dir / "stock_master.parquet", engine="pyarrow")
        df_master.to_parquet(history_path, engine="pyarrow")
        
        tradable_count = df_master['is_tradable'].sum()
        print(f"✅ 종목 마스터 갱신 완료 (총 {len(df_master)}종목 / 매매 대상 {tradable_count}종목)")
        return df_master

    def fetch_market_index_timeseries(self, upjong_cd: str, upjong_nm: str):
        """시장 지수(KOSPI/KOSDAQ) 일/주/월봉 연속 수집 및 자체 변환 적재"""
        print(f"[{upjong_cd}] {upjong_nm} 지수 | 일봉 전체 이력 수집 시작...")
        
        all_records = []
        cont_yn, next_key = "", ""
        
        while True:
            # 시장 지수 전용 TR (ka10010: 업종일주월시분요청)
            res = self.client.request(
                tr_id="ka10010", 
                endpoint="/api/dostk/mrkcond", 
                body={"upjong_cd": upjong_cd}, 
                cont_yn=cont_yn, next_key=next_key
            )
            
            if res["status"] != 200: break
            
            # 응답 키는 종목(stk_ddwkmm)과 다를 수 있으므로 동적 파싱
            data = res["data"].get("upjong_ddwkmm", res["data"].get("stk_ddwkmm", []))
            if not data: break
            all_records.extend(data)
            
            headers = res.get("header", {})
            if headers.get("cont-yn", "N") != "Y": break
            cont_yn, next_key = headers.get("cont-yn"), headers.get("next-key")

        if not all_records: return

        df = pd.DataFrame(all_records)
        
        # 거래량(trde_qty)을 포함한 수치형 전처리 로직 (종목과 동일)
        numeric_cols = ["open_pric", "high_pric", "low_pric", "close_pric", "trde_qty"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[+-]', '', regex=True), errors='coerce')

        df.rename(columns={
            "date": "timestamp", "open_pric": "open", "high_pric": "high",
            "low_pric": "low", "close_pric": "close", "trde_qty": "volume"
        }, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 시장 지수 저장 경로: D:\data\market_index\KOSPI\daily\KOSPI_daily.parquet
        market_dir = self.base_dir / "market_index" / upjong_nm
        daily_path = market_dir / "daily" / f"{upjong_nm}_daily.parquet"
        
        self._upsert_parquet(df, daily_path)
        
        # 일봉을 바탕으로 주/월봉 계산 및 저장
        df.set_index('timestamp', inplace=True)
        df_weekly = df.resample('W-FRI').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
        df_monthly = df.resample('ME').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'}).dropna().reset_index()
        
        self._upsert_parquet(df_weekly, market_dir / "weekly" / f"{upjong_nm}_weekly.parquet")
        self._upsert_parquet(df_monthly, market_dir / "monthly" / f"{upjong_nm}_monthly.parquet")
        
        print(f"✅ [{upjong_cd}] {upjong_nm} 지수 | 일/주/월봉 전체 적재 완료 (총 {len(df)}건)")    

    def _convert_and_save_resampled(self, df_daily: pd.DataFrame, stk_cd: str):
        """일봉 데이터를 주봉(W) 및 월봉(M)으로 리샘플링하여 자동 저장"""
        if df_daily.empty: return
        
        df = df_daily.copy()
        df.set_index('timestamp', inplace=True)
        
        # 주봉 생성 (금요일 마감 기준)
        df_weekly = df.resample('W-FRI').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna().reset_index()
        
        # 월봉 생성 (월말 마감 기준)
        df_monthly = df.resample('ME').agg({
            'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last', 'volume': 'sum'
        }).dropna().reset_index()
        
        weekly_path = self.stocks_dir / stk_cd / "weekly" / f"{stk_cd}_weekly.parquet"
        monthly_path = self.stocks_dir / stk_cd / "monthly" / f"{stk_cd}_monthly.parquet"
        
        self._upsert_parquet(df_weekly, weekly_path)
        self._upsert_parquet(df_monthly, monthly_path)

    def fetch_daily_timeseries(self, stk_cd: str, stk_nm: str):
        """[1] 일봉 상장 후 전체 기간 연속 수집 및 [2] 주/월봉 자동 생성"""
        print(f"[{stk_cd}] {stk_nm} | 일봉 전체 이력 수집 시작...")
        
        all_records = []
        cont_yn, next_key = "", ""
        
        while True:
            res = self.client.request(
                tr_id="ka10005", endpoint="/api/dostk/mrkcond", 
                body={"stk_cd": stk_cd}, cont_yn=cont_yn, next_key=next_key
            )
            
            if res["status"] != 200: break
            data = res["data"].get("stk_ddwkmm", [])
            if not data: break
            all_records.extend(data)
            
            headers = res.get("header", {})
            if headers.get("cont-yn", "N") != "Y": break
            cont_yn, next_key = headers.get("cont-yn"), headers.get("next-key")

        if not all_records: return

        df = pd.DataFrame(all_records)
        numeric_cols = ["open_pric", "high_pric", "low_pric", "close_pric", "trde_qty"]
        for col in numeric_cols:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[+-]', '', regex=True), errors='coerce')

        df.rename(columns={
            "date": "timestamp", "open_pric": "open", "high_pric": "high",
            "low_pric": "low", "close_pric": "close", "trde_qty": "volume"
        }, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 일봉 저장
        daily_path = self.stocks_dir / stk_cd / "daily" / f"{stk_cd}_daily.parquet"
        self._upsert_parquet(df, daily_path)
        
        # 주/월봉 자체 변환 및 저장
        self._convert_and_save_resampled(df, stk_cd)
        print(f"✅ [{stk_cd}] {stk_nm} | 일/주/월봉 전체 적재 완료 (총 {len(df)}건)")

    def fetch_minute_tick_batch(self, stk_cd: str, stk_nm: str, unit: str = "minute", tick_range: str = "1"):
        """[3] 분봉 및 틱봉 최대치 연속 수집 및 파티셔닝 적재"""
        print(f"[{stk_cd}] {stk_nm} | {unit}({tick_range}) 고빈도 데이터 수집 시작...")
        
        tr_id = "ka10006" if unit == "minute" else "ka10007"
        data_key = "stk_ddwkmm" if unit == "minute" else "stk_tick"
        
        all_records = []
        cont_yn, next_key = "", ""
        
        while True:
            res = self.client.request(
                tr_id=tr_id, endpoint="/api/dostk/mrkcond",
                body={"stk_cd": stk_cd, "tick_range": tick_range} if unit == "minute" else {"stk_cd": stk_cd},
                cont_yn=cont_yn, next_key=next_key
            )
            
            if res["status"] != 200: break
            data = res["data"].get(data_key, [])
            if not data: break
            all_records.extend(data)
            
            headers = res.get("header", {})
            if headers.get("cont-yn", "N") != "Y": break
            cont_yn, next_key = headers.get("cont-yn"), headers.get("next-key")

        if not all_records: return

        df = pd.DataFrame(all_records)
        for col in ["open_pric", "high_pric", "low_pric", "close_pric", "trde_qty"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[+-]', '', regex=True), errors='coerce')

        df.rename(columns={
            "date": "timestamp", "open_pric": "open", "high_pric": "high",
            "low_pric": "low", "close_pric": "close", "trde_qty": "volume"
        }, inplace=True)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # 월별(분봉) 또는 일별(틱봉) 파티셔닝 분리
        time_format = '%Y%m' if unit == "minute" else '%Y%m%d'
        df['partition_key'] = df['timestamp'].dt.strftime(time_format)
        
        for p_key, group in df.groupby('partition_key'):
            target_dir = self.stocks_dir / stk_cd / unit / (f"{tick_range}min" if unit == "minute" else "")
            target_dir.mkdir(parents=True, exist_ok=True)
            
            file_name = f"{stk_cd}_{tick_range}min_{p_key}.parquet" if unit == "minute" else f"{stk_cd}_tick_{p_key}.parquet"
            group = group.drop(columns=['partition_key'])
            self._upsert_parquet(group, target_dir / file_name)
            
        print(f"✅ [{stk_cd}] {stk_nm} | {unit} 데이터 파티셔닝 완료 (총 {len(df)}건)")