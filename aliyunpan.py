#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
new Env('阿里云盘签到');
cron: 10 6,18 * * *

环境变量说明:
变量名: ALIYUN_ACCOUNTS
格式: refresh_token#备注名 & refresh_token2#备注名2
提示: 多个账号用 & 或 换行 分隔；内部参数用 # 分隔。
进入网页端阿里云盘，按 F12 打开开发者工具，打开控制台输入JSON.parse(localStorage.getItem("token")).refresh_token 然后拼接#备注名即可，例如：
"""

import os
import re
import time
import logging
import requests
import random
from typing import Dict
from datetime import datetime

# ==================== 日志配置 ====================
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("AliYun")

# ---------------- 统一通知模块加载 ----------------
hadsend = False
send = None
try:
    from notify import send
    hadsend = True
    print("✅ 已加载notify.py通知模块")
except ImportError:
    print("⚠️  未加载通知模块，跳过通知功能")

# ==================== 核心逻辑 ====================
class ALiYun:
    def __init__(self, name: str, refresh_token: str):
        self.session = requests.Session()
        self.name = name
        self.refresh_token = refresh_token
        self.access_token = ""
        self.headers = {
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 AlphaDrive/3.0.0",
            "Content-Type": "application/json; charset=utf-8"
        }

    def _refresh_access_token(self) -> bool:
        """刷新 access_token"""
        url = 'https://auth.aliyundrive.com/v2/account/token'
        payload = {'grant_type': 'refresh_token', 'refresh_token': self.refresh_token}
        try:
            res = self.session.post(url, json=payload, timeout=10).json()
            if 'access_token' in res:
                self.access_token = res['access_token']
                self.refresh_token = res['refresh_token']  # 更新持久化的token
                return True
            print(f"[{self.name}] 刷新 Token 失败: {res.get('message', '未知错误')}")
            return False
        except Exception as e:
            print(f"[{self.name}] 刷新请求异常: {e}")
            return False

    def check_in(self) -> Dict:
        """执行签到"""
        url = 'https://member.aliyundrive.com/v1/activity/sign_in_list'
        headers = {**self.headers, "Authorization": f"Bearer {self.access_token}"}
        try:
            res = self.session.post(url, params={'_rx-s': 'mobile'}, json={'isReward': False}, headers=headers, timeout=10).json()
            return res
        except Exception as e:
            return {"success": False, "message": str(e)}

    def get_reward(self, day: int) -> str:
        """领取奖励"""
        url = 'https://member.aliyundrive.com/v1/activity/sign_in_reward'
        headers = {**self.headers, "Authorization": f"Bearer {self.access_token}"}
        try:
            res = self.session.post(url, params={'_rx-s': 'mobile'}, json={'signInDay': day}, headers=headers, timeout=10).json()
            return res.get('result', {}).get('notice', res.get('message', '未获取到奖励明细'))
        except Exception:
            return "奖励领取请求异常"

    def get_capacity(self) -> str:
        """查询容量"""
        def fmt(s): return f"{s/1024/1024/1024:.2f} GB" if s > 0 else "0 GB"
        url = 'https://api.aliyundrive.com/adrive/v1/user/driveCapacityDetails'
        headers = {**self.headers, "Authorization": f"Bearer {self.access_token}"}
        try:
            res = self.session.post(url, json={}, headers=headers, timeout=10).json()
            return (f"总空间: {fmt(res.get('drive_total_size', 0))}\n"
                    f"已用空间: {fmt(res.get('drive_used_size', 0))}")
        except: return "容量查询失败"

    def run(self):
        print(f"--- 账号 [{self.name}] 开始签到 ---")
        if not self._refresh_access_token():
            return f"[{self.name}] ❌ 登录失效"

        res = self.check_in()
        if not res.get('success'):
            return f"[{self.name}] ❌ 签到失败: {res.get('message')}"

        count = res.get('result', {}).get('signInCount', 0)
        reward_info = self.get_reward(count)
        cap_info = self.get_capacity()

        msg = (f"【{self.name}】签到成功！\n"
               f"本月累计签到: {count} 天\n"
               f"本次奖励: {reward_info}\n"
               f"{cap_info}")
        return msg

# ==================== 通知逻辑 ====================
def notify_user(title, content):
    """统一通知函数"""
    if hadsend:
        try:
            send(title, content)
            print(f"✅ 通知发送完成: {title}")
        except Exception as e:
            print(f"❌ 通知发送失败: {e}")
    else:
        print(f"📢 {title}\n📄 {content}")

# ==================== 主入口 ====================
def main():
    print(f"==== 阿里云盘签到开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")
    
    raw_conf = os.getenv("ALIYUN_ACCOUNTS", "")
    if not raw_conf:
        error_msg = """❌ 未找到环境变量 ALIYUN_ACCOUNTS

🔧 获取 refresh_token 的方法:
1. 打开阿里云盘网页版
2. 登录您的账号
3. 按 F12 打开开发者工具
4. 切换到 Console 标签页
5. 输入 JSON.parse(localStorage.getItem("token")).refresh_token
6. 复制输出的 refresh_token 值
7. 在 GitHub Secrets 中添加 ALIYUN_ACCOUNTS 环境变量
8. 格式: refresh_token#备注名 & refresh_token2#备注名2
"""
        print(error_msg)
        notify_user("阿里云盘签到失败", error_msg)
        return

    # 按 & 或 换行 分隔账号
    account_list = re.split(r'[&\n]+', raw_conf.strip())
    final_reports = []
    success_count = 0
    total_count = len(account_list)

    for idx, acc_str in enumerate(account_list):
        if not acc_str.strip(): continue
        
        # 按 # 分隔 token 和 备注
        parts = acc_str.split('#')
        token = parts[0].strip()
        name = parts[1].strip() if len(parts) > 1 else f"账号{idx+1}"

        if not token:
            print(f"账号 {name} 缺少 refresh_token，跳过")
            continue

        client = ALiYun(name, token)
        try:
            report = client.run()
            final_reports.append(report)
            success_count += 1
        except Exception as e:
            print(f"运行异常: {e}")
            final_reports.append(f"[{name}] 运行发生异常")
        
        # 账号间随机延迟
        if idx < len(account_list) - 1:
            delay = random.randint(3, 8)
            print(f"等待 {delay} 秒后处理下一个账号...")
            time.sleep(delay)

    if final_reports:
        print("阿里云盘签到报告", "\n" + "="*20 + "\n" + "\n\n".join(final_reports))
        
        # 发送汇总通知
        if total_count > 1:
            summary_msg = f"""📊 阿里云盘签到汇总

📈 总计: {total_count}个账号
✅ 成功: {success_count}个
❌ 失败: {total_count - success_count}个
📊 成功率: {success_count/total_count*100:.1f}%
⏰ 完成时间: {datetime.now().strftime('%m-%d %H:%M')}"""
            notify_user("阿里云盘签到汇总", summary_msg)

    print(f"\n==== 阿里云盘签到完成 - 成功{success_count}/{total_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")

def handler(event, context):
    """云函数入口"""
    main()

if __name__ == "__main__":
    main()