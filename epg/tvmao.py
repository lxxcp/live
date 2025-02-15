# -*- coding:utf-8 -*-
import requests
import time
import datetime
import re
import gzip
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as bs
from datetime import timedelta 
import random

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
    "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Referer": "https://www.tvmao.com/",
    "Sec-Fetch-Dest": "document",
    "Sec-Fetch-Mode": "navigate",
    "Sec-Fetch-Site": "same-origin",
    "Sec-Fetch-User": "?1",
    "Upgrade-Insecure-Requests": "1",
}

# 卫星频道列表
sat_channel = [
    'CCTV-CCTV1', 'CCTV-CCTV2', 'CCTV-CCTV3', 'CCTV-CCTV4', 'CCTV-CCTV5', 'CCTV-CCTV5plus', 'CCTV-CCTV6',
    'CCTV-CCTV7', 'CCTV-CCTV8', 'CCTV-CCTV9', 'CCTV-CCTV10', 'CCTV-CCTV11', 'CCTV-CCTV12', 'CCTV-CCTV13',
    'CCTV-CCTV14', 'CCTV-CCTV15', 'CCTV-CCTV16', 'CCTV-CCTV17', 'CCTV-CCTV4k', 'CETV-cetv1', 'CETV-cetv2',
    'CETV-cetv3', 'CETV-cetv4', 'btv1', 'btvjishi', 'dongfang', 'hunan', 'shandong', 'zhejiang', 'jiangsu',
    'guangdong', 'dongnan', 'anhui', 'gansu', 'liaoning', 'travel', 'neimenggu', 'ningxia', 'qinghai', 'xiamen',
    'yunnan', 'chongqing', 'jiangxi', 'shan1xi', 'shan3xi', 'shenzhen', 'sichuan', 'tianjin', 'guangxi',
    'guizhou', 'hebei', 'henan', 'heilongjiang', 'hubei', 'jilin', 'yanbian', 'xizang', 'xinjiang', 'bingtuan',
    'btvchild', 'gaoerfu', 'sdetv'
]

def get_desc(url_part):  # 获取节目介绍
    try:
        url = 'https://m.tvmao.com' + url_part
        res = requests.get(url, headers=headers, timeout=5)
        res.encoding = 'utf-8'
        soup = bs(res.text, 'html.parser')
        if soup.select('div.section'):
            desc = soup.select('div.section')[0].text
        else:
            desc = soup.select('div.d_s_info')[0].text + soup.select('div.desc_col')[0].text
    except Exception as e:
        desc = ''
    return desc.replace('\r', '\n').replace('\n\n', '\n').replace('\n\n', '\n')

def get_morning_lis(url):  # 获取当天上午的节目列表
    time.sleep(random.uniform(1, 3))  # 随机延时 1-3 秒
    max_retries = 3
    for _ in range(max_retries):
        try:
            res = requests.get(url, headers=headers, timeout=5)
            res.encoding = 'utf-8'
            soup = bs(res.text, 'html.parser')
            lis = soup.select('ul#pgrow > li')
            return lis
        except requests.exceptions.RequestException as e:
            print(f"请求失败，重试中... 错误信息: {e}")
            time.sleep(2)
    return []

def get_epgs_tvmao(channel, channel_id, date, epgs_list):
    url = f"https://www.tvmao.com/program/{channel_id}-{date.strftime('%Y%m%d')}"
    lis = get_morning_lis(url)
    if not lis:
        return {'success': False, 'msg': '无法获取节目列表'}

    epgs = []
    for li in lis:
        time_str = li.select('span.p_time')[0].text.strip()
        title = li.select('span.p_title')[0].text.strip()
        desc_url = li.select('a')[0].get('href')
        desc = get_desc(desc_url)
        epg = {
            'channel': channel,
            'title': title,
            'start_time': f"{date.strftime('%Y-%m-%d')} {time_str}",
            'desc': desc
        }
        epgs.append(epg)

    return {'success': True, 'epgs': epgs}

def generate_xml(epgs, filename):
    root = ET.Element('tv')
    for epg in epgs:
        program = ET.SubElement(root, 'programme')
        ET.SubElement(program, 'channel').text = epg['channel']['id']
        ET.SubElement(program, 'title').text = epg['title']
        ET.SubElement(program, 'start').text = epg['start_time']
        ET.SubElement(program, 'desc').text = epg['desc']
    tree = ET.ElementTree(root)
    tree.write(filename, encoding='utf-8', xml_declaration=True)

def generate_gz_xml(epgs_list, filename):
    root = ET.Element('tv')
    for epgs in epgs_list:
        for epg in epgs:
            program = ET.SubElement(root, 'programme')
            ET.SubElement(program, 'channel').text = epg['channel']['id']
            ET.SubElement(program, 'title').text = epg['title']
            ET.SubElement(program, 'start').text = epg['start_time']
            ET.SubElement(program, 'desc').text = epg['desc']
    tree = ET.ElementTree(root)
    with gzip.open(filename, 'wb') as f:
        f.write(ET.tostring(root, encoding='utf-8', xml_declaration=True))

def get_epgs_for_seven_days(channel, channel_id, start_date):
    epgs_list = []
    for i in range(7):
        date = start_date + timedelta(days=i)
        result = get_epgs_tvmao(channel, channel_id, date, epgs_list)
        if result['success']:
            epgs_list.append(result['epgs'])
    return epgs_list

def main():
    start_date = datetime.datetime.now().date()

    for channel_id in sat_channel:
        channel = {"id": channel_id, "name": channel_id}
        print(f"正在爬取频道: {channel_id}")

        # 获取一天的节目单
        dt = start_date
        result = get_epgs_tvmao(channel, channel_id, dt, None)
        if result['success']:
            generate_xml(result['epgs'], f"{channel_id}_a.xml")
            print(f"{channel_id} 一天的节目单已保存为 {channel_id}_a.xml")
        else:
            print(f"获取 {channel_id} 一天的节目单失败: {result['msg']}")

        # 获取七天的节目单
        epgs_list = get_epgs_for_seven_days(channel, channel_id, start_date)
        if epgs_list:
            generate_gz_xml(epgs_list, f"{channel_id}_a.xml.gz")
            print(f"{channel_id} 七天的节目单已保存为 {channel_id}_a.xml.gz")
        else:
            print(f"获取 {channel_id} 七天的节目单失败")

if __name__ == "__main__":
    main()