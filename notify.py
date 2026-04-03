#!/usr/bin/env python3
"""
通知模块
支持飞书、Telegram、企业微信等通知方式
"""
import json
import os
import sys
import requests

def send_feishu(webhook_url, report):
    """发送飞书通知"""
    payload = {
        "msg_type": "text",
        "content": {
            "text": f"📊 自动任务报告\n\n{report}"
        }
    }
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200

def send_telegram(bot_token, chat_id, report):
    """发送 Telegram 通知"""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": f"📊 自动任务报告\n\n{report}"
    }
    response = requests.post(url, json=payload)
    return response.status_code == 200

def send_wechat(webhook_url, report):
    """发送企业微信通知"""
    payload = {
        "msgtype": "text",
        "text": {
            "content": f"📊 自动任务报告\n\n{report}"
        }
    }
    response = requests.post(webhook_url, json=payload)
    return response.status_code == 200

def send(title, content):
    """统一发送通知函数"""
    # 从环境变量读取通知配置
    notify_method = os.environ.get('NOTIFY_METHOD', 'feishu')
    webhook_url = os.environ.get('WEBHOOK_URL', '')
    telegram_bot_token = os.environ.get('TELEGRAM_BOT_TOKEN', '')
    telegram_chat_id = os.environ.get('TELEGRAM_CHAT_ID', '')
    
    # 构建报告内容
    report = f"{title}\n\n{content}"
    
    # 发送通知
    success = False
    if notify_method == "feishu" and webhook_url:
        success = send_feishu(webhook_url, report)
    elif notify_method == "telegram" and telegram_bot_token and telegram_chat_id:
        success = send_telegram(telegram_bot_token, telegram_chat_id, report)
    elif notify_method == "wechat" and webhook_url:
        success = send_wechat(webhook_url, report)
    else:
        print("未配置通知方式或配置不完整，仅输出结果")
        print(report)
        return
    
    if success:
        print("✅ 通知已发送")
    else:
        print("❌ 通知发送失败")

def main():
    # 简单的报告内容
    report = "自动任务已执行"
    send("自动任务报告", report)

if __name__ == "__main__":
    main()