'use client';
import { useState } from 'react';

export default function SubscriptionModal() {
  const [loading, setLoading] = useState(false);

  const handleStripeCheckout = async () => {
    setLoading(true);
    try {
      // 백엔드(FastAPI)의 Stripe Checkout Session 생성 API 호출
      const res = await fetch('http://localhost:8000/api/v1/payment/create-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ plan: 'premium_quant_monthly' })
      });
      const data = await res.json();
      
      // Stripe 결제 페이지로 리다이렉트
      if (data.checkout_url) {
        window.location.href = data.checkout_url;
      }
    } catch (error) {
      console.error("결제 모듈 초기화 실패", error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="bg-[#131722] border border-gray-700 p-6 rounded-lg text-center">
      <h3 className="text-xl font-bold text-white mb-2">Premium AI Quant Access</h3>
      <p className="text-gray-400 mb-6 text-sm">실시간 AI 매매 시그널과 TradingView 프리미엄 차트 분석 기능을 무제한으로 사용하세요.</p>
      <button 
        onClick={handleStripeCheckout}
        disabled={loading}
        className="bg-indigo-600 hover:bg-indigo-500 text-white font-bold py-3 px-8 rounded transition-colors w-full"
      >
        {loading ? 'Processing...' : 'Subscribe with Stripe ($49/mo)'}
      </button>
    </div>
  );
}