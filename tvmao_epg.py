# -*- coding:utf-8 -*-
import requests
import time
import datetime
import re
from bs4 import BeautifulSoup as bs
import xml.etree.ElementTree as ET

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
}

# 获取节目介绍（暂不使用）
def get_desc(url_part):
    return ""

# 获取当天上午的节目单
def get_morning_lis(url, today):
    res = requests.get(url, headers=headers, timeout=5)
    res.encoding = "utf-8"
    soup = bs(res.text, "html.parser")
    lis = soup.select("ul#pgrow > li")
    return lis

# 获取 TVMAO 的 token
def get_token():
    url = "https://www.tvmao.com/servlet/accessToken?p=channelEpg"
    res = requests.get(url, headers=headers, timeout=5)
    res.encoding = "utf-8"
    res_json = res.json()
    token = res_json[1] if res_json[0] else ""
    return token

# 获取某个频道的节目单
def get_epgs_tvmao(channel_id, dt):
    afternoon_url = "https://www.tvmao.com/servlet/channelEpg"
    epgs = []
    today_dt = datetime.datetime.now()
    need_weekday = dt.weekday() + 1  # 需要获取周几的节目
    epg_url_part = "http://m.tvmao.com/program/"
    url = f"{epg_url_part}{channel_id}-w{need_weekday}.html"

    try:
        # 获取上午节目单
        lis = get_morning_lis(url, today_dt.date() == dt)
        for li in lis:
            if "id" in li.attrs:
                continue
            title = li.select("span.p_show")[0].text
            starttime_str = li.select("span.am")[0].text.strip()
            if starttime_str == "直播中" or "正在播出" in starttime_str:
                starttime = today_dt
            else:
                starttime = datetime.datetime.combine(
                    dt, datetime.time(int(starttime_str[:2]), int(starttime_str[-2:]))
                )
            epg = {
                "channel_id": channel_id,
                "starttime": starttime,
                "title": title,
                "desc": "",
            }
            epgs.append(epg)

        # 获取下午节目单
        tccc = channel_id.split("-")
        tc = tccc[0] if len(tccc) == 2 else "digital"
        cc = tccc[1] if len(tccc) == 2 else "-".join(tccc[1:])
        data = {
            "tc": tc,
            "cc": cc,
            "w": need_weekday,
            "token": get_token(),
        }
        res = requests.post(afternoon_url, headers=headers, data=data, timeout=30)
        lss = res.json()[1]

        if isinstance(lss, str):  # 处理 HTML 格式的下午节目单
            soup = bs(lss, "html.parser")
            lis1 = soup.select("li")
            for tr in lis1:
                if not tr.find("div"):
                    continue
                spans = tr.select("span")
                if len(spans) > 1:
                    title = spans[1].text
                    starttime_str = spans[0].text.replace("正在播出", "").strip()
                    starttime = datetime.datetime.combine(
                        dt, datetime.time(int(starttime_str[:2]), int(starttime_str[-2:]))
                    )
                    epg = {
                        "channel_id": channel_id,
                        "starttime": starttime,
                        "title": title,
                        "desc": "",
                    }
                    epgs.append(epg)
        else:  # 处理 JSON 格式的下午节目单
            for tr in lss:
                tr1 = bs(tr["program"], "html.parser")
                title = tr1.text
                starttime_str = tr["time"]
                starttime = datetime.datetime.combine(
                    dt, datetime.time(int(starttime_str[:2]), int(starttime_str[-2:]))
                )
                epg = {
                    "channel_id": channel_id,
                    "starttime": starttime,
                    "title": title,
                    "desc": "",
                }
                epgs.append(epg)
    except Exception as e:
        print(f"Failed to fetch EPG for channel {channel_id}: {e}")
    return epgs

# 获取所有频道
def get_channels_tvmao():
    url_sort = "https://www.tvmao.com/program/playing/"
    res = requests.get(url_sort, headers=headers, timeout=5)
    res.encoding = "utf-8"
    soup = bs(res.text, "html.parser")
    channels = []
    provinces_more = soup.select("div.province > ul.province-list > li")
    big_sorts_more = soup.select("dl.chntypetab > dd")

    for province_more in provinces_more:
        province = province_more.text.strip().replace("黑龙", "黑龙江")
        province_id = province_more.a["href"].replace("/program/playing/", "").replace("/", "")
        url = f"https://www.tvmao.com/program/playing/{province_id}"
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = "utf-8"
        soup = bs(res.text, "html.parser")
        channel_trs = soup.select("table.timetable > tr")
        for tr in channel_trs:
            tr1 = tr.td.a
            name = tr1["title"]
            href = tr1["href"]
            id = (
                href.replace("/program/", "")
                .replace("/", "-")
                .replace(".html", "")
                .replace("-program_", "")
            )
            id = re.sub("-w\d$", "", id)
            channel = {
                "name": name,
                "id": id,
                "url": f"https://m.tvmao.com/program/{id}.html",
            }
            channels.append(channel)
    return channels

# 保存节目单为 XML 文件
def save_epg_to_xml(channels, days=5, filename="tvmao.xml"):
    root = ET.Element("tv")
    for channel in channels:
        channel_id = channel["id"]
        channel_name = channel["name"]
        channel_elem = ET.SubElement(root, "channel", id=channel_id, name=channel_name)
        for i in range(days):
            dt = datetime.datetime.now() + datetime.timedelta(days=i)
            epgs = get_epgs_tvmao(channel_id, dt.date())
            for epg in epgs:
                program_elem = ET.SubElement(channel_elem, "program")
                ET.SubElement(program_elem, "starttime").text = epg["starttime"].strftime("%Y-%m-%d %H:%M:%S")
                ET.SubElement(program_elem, "title").text = epg["title"]
                ET.SubElement(program_elem, "desc").text = epg["desc"]
    tree = ET.ElementTree(root)
    tree.write(filename, encoding="utf-8", xml_declaration=True)
    print(f"EPG data saved to {filename}")

# 主函数
if __name__ == "__main__":
    # 获取所有频道
    channels = get_channels_tvmao()
    # 保存节目单为 XML 文件
    save_epg_to_xml(channels, days=5, filename="tvmao.xml")