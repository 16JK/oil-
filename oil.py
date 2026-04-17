import ccxt
import time
import requests
import json
from datetime import datetime

# ========== 配置区域 ==========
WEBHOOK_URL = "填这里"  # 替换为真实地址
SYMBOLS = ["XBR_USDT", "XTI_USDT"]          # 监控的两个品种
CHECK_INTERVAL = 1800                      # 1800秒 = 半小时
# =============================

def send_wechat_bot(content):
    """发送文本消息到企业微信群机器人"""
    headers = {"Content-Type": "application/json"}
    data = {
        "msgtype": "text",
        "text": {"content": content}
    }
    try:
        resp = requests.post(WEBHOOK_URL, headers=headers, data=json.dumps(data), timeout=10)
        result = resp.json()
        if result.get("errcode") == 0:
            print("消息发送成功")
        else:
            print(f"消息发送失败: {result}")
    except Exception as e:
        print(f"发送消息异常: {e}")

def fetch_gate_data(symbol):
    """从Gate.io获取指定合约的最新价和资金费率"""
    exchange = ccxt.gateio({
        'options': {
            'defaultType': 'swap',  # 指定为永续合约
        }
    })
    try:
        # 获取 ticker (包含最新价 last)
        ticker = exchange.fetch_ticker(symbol)
        price = ticker['last']

        # 获取资金费率 (需要传递参数，Gate.io 可能要求 symbol 带 :USDT 后缀，但 ccxt 会自动处理)
        funding_rate = None
        try:
            # 有些交易所 fetch_funding_rate 需要合约参数，Gate.io 可能用 fetchFundingRate
            funding = exchange.fetch_funding_rate(symbol)
            funding_rate = funding['fundingRate']
        except Exception as e:
            print(f"获取资金费率失败: {e}")
            funding_rate = 'N/A'

        return {
            'symbol': symbol,
            'price': price,
            'funding_rate': funding_rate,
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        print(f"获取 {symbol} 数据失败: {e}")
        return None

def calculate_spread(data1, data2):
    """计算两个品种之间的价差（价格差和资金费率差）"""
    if data1 and data2:
        price1 = data1['price']
        price2 = data2['price']
        price_diff = price1 - price2
        price_diff_percent = (price_diff / ((price1 + price2) / 2)) * 100

        fr1 = data1['funding_rate']
        fr2 = data2['funding_rate']
        fr_diff = None
        if fr1 != 'N/A' and fr2 != 'N/A':
            fr_diff = fr1 - fr2

        return price_diff, price_diff_percent, fr_diff
    return None, None, None

def format_message(data1, data2):
    """构造推送消息"""
    if not data1 or not data2:
        return "❌ 获取数据失败，请检查网络或品种代码"

    price_diff, price_diff_percent, fr_diff = calculate_spread(data1, data2)

    msg = f"🔔 **Gate.io 双品种监控**\n"
    msg += f"⏰ 时间：{data1['time']}\n\n"

    # 品种1
    msg += f"📈 **{data1['symbol']}**\n"
    msg += f"  价格：{data1['price']:.4f}\n"
    msg += f"  资金费率：{data1['funding_rate'] if data1['funding_rate']!='N/A' else 'N/A'}\n\n"

    # 品种2
    msg += f"📉 **{data2['symbol']}**\n"
    msg += f"  价格：{data2['price']:.4f}\n"
    msg += f"  资金费率：{data2['funding_rate'] if data2['funding_rate']!='N/A' else 'N/A'}\n\n"

    # 价差
    msg += f"⚖️ **价差分析**\n"
    msg += f"  价格差 (XBR - XTI)：{price_diff:.4f} USDT\n"
    msg += f"  价格差百分比：{price_diff_percent:.2f}%\n"
    if fr_diff is not None:
        msg += f"  资金费率差：{fr_diff:.6f}\n"
    else:
        msg += f"  资金费率差：N/A\n"

    return msg

def main():
    print("Gate.io 双品种监控启动，每半小时推送一次...")
    while True:
        data_list = []
        for sym in SYMBOLS:
            data = fetch_gate_data(sym)
            if data:
                data_list.append(data)
            time.sleep(1)  # 避免请求过快

        if len(data_list) == 2:
            msg = format_message(data_list[0], data_list[1])
        else:
            msg = "❌ 未能获取全部品种数据，请稍后重试"

        send_wechat_bot(msg)
        print(f"[{datetime.now()}] 推送完成，等待 {CHECK_INTERVAL//60} 分钟...")
        time.sleep(CHECK_INTERVAL)

if __name__ == "__main__":
    main()