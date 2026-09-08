'use client';
import { useEffect, useRef, useState } from 'react';
import { createChart, IChartApi, ISeriesApi } from 'lightweight-charts';

export default function QuantDashboard() {
  const chartContainer = useRef<HTMLDivElement>(null);
  const chart = useRef<IChartApi | null>(null);
  const candleSeries = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const [logs, setLogs] = useState<any[]>([]);

  useEffect(() => {
    // TradingView Lightweight Charts 초기화
    chart.current = createChart(chartContainer.current!, {
      layout: { background: { color: '#0B0E14' }, textColor: '#D1D4DC' },
      grid: { vertLines: { color: '#1F2937' }, horzLines: { color: '#1F2937' } },
      width: chartContainer.current?.clientWidth,
      height: 600,
    });
    
    candleSeries.current = chart.current.addCandlestickSeries({
      upColor: '#F87171', downColor: '#60A5FA', borderVisible: false, wickUpColor: '#F87171', wickDownColor: '#60A5FA'
    });
    
    // REST API를 통해 백엔드의 Parquet 시계열 데이터 로드
    fetch('http://localhost:8000/api/v1/chart/005930')
      .then(res => res.json())
      .then(result => candleSeries.current?.setData(result.data));

    // FastAPI WebSocket 연동 (실시간 체결 시그널 수신)
    const ws = new WebSocket('ws://localhost:8000/ws/trading');
    ws.onmessage = (event) => {
      const data = JSON.parse(event.data);
      if (data.event === 'TRADE') {
        setLogs(prev => [data, ...prev]);
        candleSeries.current?.setMarkers([{ 
          time: (new Date(data.timestamp).getTime() / 1000) as any, 
          position: data.action === 'BUY' ? 'belowBar' : 'aboveBar', 
          color: data.action === 'BUY' ? '#F87171' : '#60A5FA', 
          shape: data.action === 'BUY' ? 'arrowUp' : 'arrowDown', 
          text: `AI ${data.probability}%` 
        }]);
      }
    };

    return () => { chart.current?.remove(); ws.close(); };
  }, []);

  return (
    <div className="bg-[#0B0E14] text-white min-h-screen p-6 grid grid-cols-4 gap-6">
      <div className="col-span-3 border border-gray-800 shadow-xl rounded-lg overflow-hidden">
        <div className="p-4 bg-[#131722] border-b border-gray-800">
          <h1 className="text-xl font-bold font-sans">AI Quant Console - Samsung (005930)</h1>
        </div>
        <div ref={chartContainer} />
      </div>
      <div className="col-span-1 border border-gray-800 rounded-lg p-4 bg-[#131722] flex flex-col">
        <h2 className="text-lg font-bold mb-4 border-b border-gray-700 pb-2">Execution Logs</h2>
        <div className="overflow-y-auto flex-1 font-mono text-sm space-y-3">
          {logs.map((log, idx) => (
            <div key={idx} className="p-3 rounded-md bg-gray-900/50 border border-gray-700">
              <div className={`font-bold ${log.action === 'BUY' ? 'text-red-400' : 'text-blue-400'}`}>
                {log.action} {log.stk_cd} <span className="float-right">{log.probability}%</span>
              </div>
              <div className="text-gray-400 mt-1">Price: ₩{log.price.toLocaleString()}</div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}