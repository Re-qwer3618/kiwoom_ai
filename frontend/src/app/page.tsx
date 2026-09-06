'use client';
import { useEffect, useState, useRef } from 'react';
import { createChart } from 'lightweight-charts';

export default function Dashboard() {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  const [balance, setBalance] = useState({ dbst_bal: 0, tot_evlt_amt: 0 });
  const [logs, setLogs] = useState<string[]>([]);

  useEffect(() => {
    // 1. 차트 초기화
    const chart = createChart(chartContainerRef.current!, {
      layout: { background: { color: '#131722' }, textColor: '#d1d4dc' },
      grid: { vertLines: { color: '#2a2e39' }, horzLines: { color: '#2a2e39' } },
      width: 800,
      height: 400,
    });
    const candlestickSeries = chart.addCandlestickSeries();

    // 2. FastAPI WebSocket 연동
    const ws = new WebSocket('ws://localhost:8000/ws/market');
    ws.onmessage = (event) => {
      const message = JSON.parse(event.data);
      if (message.type === 'TRADE_SIGNAL') {
        setLogs(prev => [`[${message.timestamp}] ${message.action} ${message.stk_cd} (확률: ${message.probability})`, ...prev]);
      }
    };

    return () => { chart.remove(); ws.close(); };
  }, []);

  return (
    <div className="min-h-screen bg-gray-900 text-white p-8 font-sans">
      <h1 className="text-3xl font-bold mb-6">AI Quant Trading Dashboard</h1>
      
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 bg-gray-800 p-4 rounded-lg shadow-lg">
          <h2 className="text-xl mb-4 border-b border-gray-700 pb-2">실시간 차트 모니터링</h2>
          <div ref={chartContainerRef} />
        </div>
        
        <div className="bg-gray-800 p-4 rounded-lg shadow-lg flex flex-col">
          <h2 className="text-xl mb-4 border-b border-gray-700 pb-2">AI 매매 시그널 로그</h2>
          <div className="flex-1 overflow-y-auto space-y-2 text-sm">
            {logs.map((log, idx) => (
              <div key={idx} className="p-2 bg-gray-700 rounded text-green-400">{log}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}