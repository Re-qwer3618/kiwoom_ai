import 'package:flutter/material.dart';
import 'package:web_socket_channel/web_socket_channel.dart';
import 'dart:convert';

void main() => runApp(const AIQuantMobileApp());

class AIQuantMobileApp extends StatelessWidget {
  const AIQuantMobileApp({super.key});

  @override
  Widget build(BuildContext context) {
    return MaterialApp(
      debugShowCheckedModeBanner: false,
      theme: ThemeData.dark().copyWith(scaffoldBackgroundColor: const Color(0xFF0B0E14)),
      home: const TradingMonitorScreen(),
    );
  }
}

class TradingMonitorScreen extends StatefulWidget {
  const TradingMonitorScreen({super.key});
  @override
  State<TradingMonitorScreen> createState() => _TradingMonitorScreenState();
}

class _TradingMonitorScreenState extends State<TradingMonitorScreen> {
  // 실제 스마트폰 구동 시 PC의 로컬망 IP(예: 192.168.x.x)로 변경 필요
  final _channel = WebSocketChannel.connect(Uri.parse('ws://10.0.2.2:8000/ws/trading'));
  final List<Map<String, dynamic>> _logs = [];

  void _activateKillSwitch() {
    _channel.sink.add(jsonEncode({"action": "KILL_SWITCH"}));
    ScaffoldMessenger.of(context).showSnackBar(
      const SnackBar(
        content: Text('긴급 킬스위치 전송 완료. 전량 시장가 청산 대기중.', style: TextStyle(fontWeight: FontWeight.bold)), 
        backgroundColor: Colors.redAccent
      ),
    );
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(
        title: const Text('AI Remote Monitor', style: TextStyle(fontWeight: FontWeight.bold, letterSpacing: 1.2)),
        backgroundColor: const Color(0xFF131722),
        elevation: 0,
      ),
      body: StreamBuilder(
        stream: _channel.stream,
        builder: (context, snapshot) {
          if (snapshot.hasData) {
            final data = jsonDecode(snapshot.data);
            if (data['event'] == 'TRADE') _logs.insert(0, data);
          }
          return ListView.separated(
            padding: const EdgeInsets.all(12),
            itemCount: _logs.length,
            separatorBuilder: (_, __) => const SizedBox(height: 8),
            itemBuilder: (context, index) {
              final log = _logs[index];
              final isBuy = log['action'] == 'BUY';
              return Container(
                decoration: BoxDecoration(
                  color: const Color(0xFF131722),
                  borderRadius: BorderRadius.circular(8),
                  border: Border.all(color: isBuy ? Colors.red.withOpacity(0.3) : Colors.teal.withOpacity(0.3)),
                ),
                child: ListTile(
                  leading: CircleAvatar(
                    backgroundColor: isBuy ? Colors.redAccent.withOpacity(0.2) : Colors.tealAccent.withOpacity(0.2),
                    child: Icon(isBuy ? Icons.arrow_upward : Icons.arrow_downward, color: isBuy ? Colors.redAccent : Colors.tealAccent),
                  ),
                  title: Text('${log['action']} ${log['stk_cd']}', style: const TextStyle(fontWeight: FontWeight.bold)),
                  subtitle: Text('₩${log['price']} | Prob: ${log['probability']}%'),
                  trailing: const Icon(Icons.show_chart, color: Colors.grey),
                ),
              );
            },
          );
        },
      ),
      floatingActionButton: FloatingActionButton.extended(
        backgroundColor: Colors.red[800],
        elevation: 8,
        icon: const Icon(Icons.power_settings_new, color: Colors.white),
        label: const Text('KILL SWITCH', style: TextStyle(color: Colors.white, fontWeight: FontWeight.bold, letterSpacing: 1.5)),
        onPressed: _activateKillSwitch,
      ),
      floatingActionButtonLocation: FloatingActionButtonLocation.centerFloat,
    );
  }

  @override
  void dispose() {
    _channel.sink.close();
    super.dispose();
  }
}