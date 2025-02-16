import requests
import json
from datetime import datetime, timedelta
import xml.etree.ElementTree as ET

# TVMAO 的 API 地址（假设）
TVMAO_API_URL = "https://api.tvmao.com/program/epg"

# 请求头，模拟浏览器请求
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
}

# 获取所有频道的 ID（假设通过 API 获取）
def get_all_channel_ids():
    """
    获取 TVMAO 所有频道的 ID
    """
    try:
        response = requests.get("https://api.tvmao.com/channels", headers=HEADERS)
        response.raise_for_status()  # 检查请求是否成功
        channels = response.json().get("data", [])
        return [channel["id"] for channel in channels]
    except Exception as e:
        print(f"Failed to fetch channel IDs: {e}")
        return []

# 获取某个频道未来五天的节目表
def get_channel_epg(channel_id, days=5):
    """
    获取某个频道未来几天的节目表
    :param channel_id: 频道 ID
    :param days: 需要获取的天数
    :return: 节目表数据
    """
    epg_data = []
    for i in range(days):
        date = (datetime.now() + timedelta(days=i)).strftime("%Y-%m-%d")  # 计算日期
        try:
            params = {
                "channel_id": channel_id,
                "date": date,
            }
            response = requests.get(TVMAO_API_URL, headers=HEADERS, params=params)
            response.raise_for_status()  # 检查请求是否成功
            epg_data.extend(response.json().get("data", []))
        except Exception as e:
            print(f"Failed to fetch EPG for channel {channel_id} on {date}: {e}")
    return epg_data

# 获取所有频道未来五天的节目表
def get_all_epg(days=5):
    """
    获取所有频道未来几天的节目表
    :param days: 需要获取的天数
    :return: 所有频道的节目表数据
    """
    channel_ids = get_all_channel_ids()
    if not channel_ids:
        print("No channel IDs found.")
        return {}

    all_epg = {}
    for channel_id in channel_ids:
        print(f"Fetching EPG for channel {channel_id}...")
        epg = get_channel_epg(channel_id, days)
        if epg:
            all_epg[channel_id] = epg
    return all_epg

# 将节目表数据保存为 XML 文件
def save_epg_to_xml(epg_data, filename="tvmao.xml"):
    """
    将节目表数据保存为 XML 文件
    :param epg_data: 节目表数据
    :param filename: 保存的文件名
    """
    try:
        # 创建 XML 根元素
        root = ET.Element("tv")

        # 遍历所有频道的节目表
        for channel_id, programs in epg_data.items():
            # 创建频道元素
            channel_elem = ET.SubElement(root, "channel", id=str(channel_id))

            # 遍历节目表
            for program in programs:
                # 创建节目元素
                program_elem = ET.SubElement(channel_elem, "program")
                # 添加节目信息
                for key, value in program.items():
                    ET.SubElement(program_elem, key).text = str(value)

        # 创建 XML 树并写入文件
        tree = ET.ElementTree(root)
        tree.write(filename, encoding="utf-8", xml_declaration=True)
        print(f"EPG data saved to {filename}")
    except Exception as e:
        print(f"Failed to save EPG data as XML: {e}")

# 主函数
if __name__ == "__main__":
    # 获取所有频道未来五天的节目表
    epg_data = get_all_epg(days=5)

    # 保存节目表数据到 XML 文件
    save_epg_to_xml(epg_data)