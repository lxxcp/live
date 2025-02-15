# -*- coding:utf-8 -*-
import requests
import time
import datetime
import re
import gzip
import xml.etree.ElementTree as ET
from bs4 import BeautifulSoup as bs
from datetime import timedelta

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
}

# 卫星频道列表
sat_channel = [
   ['CCTV-CCTV1','CCTV-CCTV2','CCTV-CCTV3','CCTV-CCTV4','CCTV-CCTV5','CCTV-CCTV5plus','CCTV-CCTV6', 'CCTV-CCTV7','CCTV-CCTV8','CCTV-CCTV9','CCTV-CCTV10','CCTV-CCTV11','CCTV-CCTV12','CCTV-CCTV13', 'CCTV-CCTV14',  'CCTV-CCTV15','CCTV-CCTV16','CCTV-CCTV17','CCTV-CCTV4k', 'CETV-cetv1', 'CETV-cetv2', 'CETV-cetv3', 'CETV-cetv4', 'btv1', 'btvjishi', 'dongfang', 'hunan', 'shandong', 'zhejiang', 'jiangsu', 'guangdong', 'dongnan', 'anhui', 'gansu', 'liaoning', 'travel', 'neimenggu', 'ningxia', 'qinghai', 'xiamen','yunnan', 'chongqing', jiangxi', 'shan1xi', 'shan3xi', 'shenzhen', 'sichuan', 'tianjin','guangxi', 'guizhou', 'hebei', 'henan', 'heilongjiang', 'hubei', 'jilin','yanbian', 'xizang', 'xinjiang', 'bingtuan', 'btvchild', 'gaoerfu', 'sdetv']

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
    res = requests.get(url, headers=headers, timeout=5)
    res.encoding = 'utf-8'
    soup = bs(res.text, 'html.parser')
    lis = soup.select('ul#pgrow > li')
    return lis

def get_token():
    url = 'https://www.tvmao.com/servlet/accessToken?p=channelEpg'
    res = requests.get(url, headers=headers, timeout=5)
    res.encoding = 'utf-8'
    res_json = res.json()
    success = 1 if res_json[0] else 0
    token = res_json[1]
    return {'success': success, 'token': token}

def get_epgs_tvmao(channel, channel_id, dt, func_arg):
    afternoon_url = 'https://www.tvmao.com/servlet/channelEpg'
    time.sleep(4)  # 防止被BAN
    sleep_time = 10  # 出错时等待时间
    epgs = []
    msg = ''
    success = 1
    ban = 0  # 标识是否被BAN掉了
    today_dt = datetime.datetime.now()
    need_weekday = dt.weekday() + 1  # 需要获取周几的节目可以获取下周数据 w8 下周一 w9下周二
    epg_url_part = 'http://m.tvmao.com/program/'
    url = '%s%s-w%s.html' % (epg_url_part, channel_id, need_weekday)
    try:
        nn, lis = 0, []
        while len(lis) == 0:  # 如果没有返回上午节目重新抓取上午节目，防止tvmao不稳定
            lis = get_morning_lis(url)
            time.sleep(0.7)
            nn += 1
            if nn > 3:
                break
        time.sleep(0.5)
    except Exception as e:
        msg = 'spider-tvmao-get_morning_lis获取上午数据失败！%s' % (e)
        success = 0
        return {'success': success, 'epgs': epgs, 'msg': msg, 'last_program_date': dt}

    for li in lis:
        if "id" in li.attrs:
            continue
        title = li.select('span.p_show')[0].text
        starttime_str = li.select('span.am')[0].text.strip()
        if starttime_str == '直播中' or '正在播出' in starttime_str.strip():
            starttime = today_dt
        else:
            starttime = datetime.datetime.combine(dt, datetime.time(int(starttime_str[:2]), int(starttime_str[-2:])))
        href = li.a['href'] if 'href' in str(li.a) else ''
        desc = get_desc(href)
        url = 'https://www.tvmao.com' + href.replace('tvcolumn', 'drama')
        epg = {
            'channel_id': channel.id,
            'starttime': starttime,
            'endtime': None,
            'title': title,
            'desc': desc,
            'program_date': dt,
        }
        epgs.append(epg)

    try:
        tccc = channel_id.split('-')
        if len(tccc) == 2:
            tc, cc = tccc
        else:
            tc = 'digital'
            cc = '-'.join(tccc[1:])
        data = {
            'tc': tc,
            'cc': cc,
            'w': need_weekday,
            'token': get_token()['token'],
        }
        res = requests.post(afternoon_url, headers=headers, data=data, timeout=30)
        lss = res.json()[1]
        if res.json()[0] == -2:
            msg = '^v^========被电视猫BAN掉了，等待 %s 秒！' % sleep_time
            time.sleep(sleep_time)
            success = 0
            ban = 1
            return {'success': success, 'epgs': epgs, 'msg': msg, 'last_program_date': dt, 'ban': ban}

        if isinstance(lss, str):
            soup = bs(lss, 'html.parser')
            lis1 = soup.select('li')
            for tr in lis1:
                if not tr.find('div'):
                    continue
                spans = tr.select('span')
                if len(spans) > 1:
                    title = spans[1].text
                starttime_str = spans[0].text.replace('正在播出', '').strip()
                starttime = datetime.datetime.combine(dt, datetime.time(int(starttime_str[:2]), int(starttime_str[-2:])))
                epg = {
                    'channel_id': channel.id,
                    'starttime': starttime,
                    'endtime': None,
                    'title': title,
                    'desc': '',
                    'program_date': dt,
                }
                epgs.append(epg)
        else:
            for tr in lss:
                tr1 = bs(tr['program'], 'html.parser')
                title = tr1.text
                starttime_str = tr['time']
                starttime = datetime.datetime.combine(dt, datetime.time(int(starttime_str[:2]), int(starttime_str[-2:])))
                href = tr1.a['href'] if 'href' in str(tr1.a) else ''
                program_url = 'https://www.tvmao.com' + href.replace('tvcolumn', 'drama')
                desc = get_desc(href)
                epg = {
                    'channel_id': channel.id,
                    'starttime': starttime,
                    'endtime': None,
                    'title': title,
                    'desc': desc,
                    'program_date': dt,
                }
                epgs.append(epg)
    except Exception as e:
        success = 0
        msg = 'spider-tvmao-%s' % e
    return {'success': success, 'epgs': epgs, 'msg': msg, 'last_program_date': dt, 'ban': 0, 'source': 'tvmao'}

def generate_xml(epgs, filename):
    """将节目单数据生成 XML 文件"""
    root = ET.Element("programs")
    for epg in epgs:
        program = ET.SubElement(root, "program")
        for key, value in epg.items():
            if key == "starttime" or key == "endtime":
                value = value.strftime("%Y-%m-%d %H:%M:%S") if value else ""
            child = ET.SubElement(program, key)
            child.text = str(value)
    tree = ET.ElementTree(root)
    tree.write(filename, encoding="utf-8", xml_declaration=True)

def generate_gz_xml(epgs_list, filename):
    """将七天的节目单数据生成 XML 并压缩为 GZ 文件"""
    root = ET.Element("programs")
    for epgs in epgs_list:
        day = ET.SubElement(root, "day")
        for epg in epgs:
            program = ET.SubElement(day, "program")
            for key, value in epg.items():
                if key == "starttime" or key == "endtime":
                    value = value.strftime("%Y-%m-%d %H:%M:%S") if value else ""
                child = ET.SubElement(program, key)
                child.text = str(value)
    tree = ET.ElementTree(root)
    tree.write("temp.xml", encoding="utf-8", xml_declaration=True)
    
    # 压缩为 GZ 文件
    with open("temp.xml", "rb") as f_in:
        with gzip.open(filename, "wb") as f_out:
            f_out.writelines(f_in)

def get_epgs_for_seven_days(channel, channel_id, start_date):
    """获取七天的节目单"""
    epgs_list = []
    for i in range(7):
        dt = start_date + timedelta(days=i)
        result = get_epgs_tvmao(channel, channel_id, dt, None)
        if result['success']:
            epgs_list.append(result['epgs'])
        else:
            print(f"获取 {dt} 的节目单失败: {result['msg']}")
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