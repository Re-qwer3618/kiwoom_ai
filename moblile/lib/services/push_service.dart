import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

class PushNotificationService {
  final FirebaseMessaging _fcm = FirebaseMessaging.instance;
  final FlutterLocalNotificationsPlugin _localNotifications = FlutterLocalNotificationsPlugin();

  Future<void> initialize() async {
    // 알림 권한 요청
    await _fcm.requestPermission(alert: true, badge: true, sound: true);
    
    // 디바이스 토큰 확보 (FastAPI 서버로 전송하여 유저 매핑)
    String? token = await _fcm.getToken();
    print("📱 FCM Device Token: $token");

    // 로컬 푸시 알림 채널 설정 (안드로이드 헤드업 알림용)
    const AndroidNotificationChannel channel = AndroidNotificationChannel(
      'quant_trade_alerts', 'AI Trade Alerts',
      description: 'AI 매매 체결 및 킬스위치 경고 알림',
      importance: Importance.max,
    );

    await _localNotifications
        .resolvePlatformSpecificImplementation<AndroidFlutterLocalNotificationsPlugin>()
        ?.createNotificationChannel(channel);

    // 포그라운드 메시지 수신 리스너
    FirebaseMessaging.onMessage.listen((RemoteMessage message) {
      RemoteNotification? notification = message.notification;
      AndroidNotification? android = message.notification?.android;

      if (notification != null && android != null) {
        _localNotifications.show(
          notification.hashCode,
          notification.title,
          notification.body,
          NotificationDetails(
            android: AndroidNotificationDetails(
              channel.id, channel.name,
              channelDescription: channel.description,
              icon: '@mipmap/ic_launcher',
              color: const Color(0xFFE53935), // 긴급 알림 색상
            ),
          ),
        );
      }
    });
  }
}