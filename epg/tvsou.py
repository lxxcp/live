# -*- coding: utf-8 -*-
import re
import pytz
import requests
from lxml import html
from datetime import datetime, timezone, timedelta

tz = pytz.timezone('Asia/Shanghai')

cctv_channel = ['cctv1', 'cctv2', 'cctv3', 'cctv4', 'cctv5', 'cctv5plus', 'cctv6',
                'cctv7', 'cctv8', 'cctvjilu', 'cctv10', 'cctv11', 'cctv12', 'cctvchild',
                'cctv15', 'cctv16', 'cctv17', 'cctv4k']
cctv_channel_tvsou = ['cctv-1', 'cctv-2', 'cctv-3', 'cctv-4', 'cctv-5', 'cctv5+', 'cctv-6',
                      'cctv-7', 'cctv-8', 'cctv-9', 'cctv-10', 'cctv-11', 'cctv-12']

sat_channel = ['cetv1', 'cetv2', 'cetv3', 'cetv4', 'btv1', 'btvjishi', 'dongfang',
               'hunan', 'shandong', 'zhejiang', 'jiangsu', 'guangdong', 'dongnan', 'anhui',
               'gansu', 'liaoning', 'travel', 'neimenggu', 'ningxia', 'qinghai', 'xiamen',
               'yunnan', 'chongqing', 'jiangxi', 'shan1xi', 'shan3xi', 'shenzhen', 'sichuan', 'tianjin',
               'guangxi', 'guizhou', 'hebei', 'henan', 'heilongjiang', 'hubei', 'jilin',
               'yanbian', 'xizang', 'xinjiang', 'bingtuan', 'btvchild', 'gaoerfu', 'sdetv']
sat_channel_tvsou = ['hubei', 'hunan', 'zhejiang', 'jiangsu', 'dongfang', 'btv1', 'guangdong',
                     'shenzhen', 'heilongjiang', 'tianjin', 'shandong', 'anhui', 'liaoning']

def getChannelCNTV(fhandle, channelID):
    '''
    通过央视 CNTV 接口，获取央视和上星卫视的节目单，写入同目录下 guide.xml 文件，文件格式符合 xmltv 标准
    '''
    cids = ','.join(channelID)
    epgdate = datetime.now(tz).strftime('%Y%m%d')
    session = requests.Session()
    api = f"http://api.cntv.cn/epg/epginfo?c={cids}&d={epgdate}"
    epgdata = session.get(api).json()

    for channel in channelID:
        fhandle.write(f'    <channel id="{channel}">\n')
        fhandle.write(f'        <display-name lang="cn">{epgdata[channel]["channelName"]}</display-name>\n')
        fhandle.write('    </channel>\n')

def getChannelEPG(fhandle, channelID):
    '''
    获取节目详情并写入 XML 文件
    '''
    cids = ','.join(channelID)
    epgdate = datetime.now(tz).strftime('%Y%m%d')
    epgdate2 = (datetime.now(tz) + timedelta(days=1)).strftime('%Y%m%d')
    epgdate3 = (datetime.now(tz) + timedelta(days=2)).strftime('%Y%m%d')
    session = requests.Session()
    api = f"http://api.cntv.cn/epg/epginfo?c={cids}&d={epgdate}"
    api2 = f"http://api.cntv.cn/epg/epginfo?c={cids}&d={epgdate2}"
    api3 = f"http://api.cntv.cn/epg/epginfo?c={cids}&d={epgdate3}"
    epgdata = session.get(api).json()
    epgdata2 = session.get(api2).json()
    epgdata3 = session.get(api3).json()

    for channel in channelID:
        for program in [epgdata[channel]['program'], epgdata2[channel]['program'], epgdata3[channel]['program']]:
            for detail in program:
                st = datetime.fromtimestamp(detail['st']).strftime('%Y%m%d%H%M%S')
                et = datetime.fromtimestamp(detail['et']).strftime('%Y%m%d%H%M%S')
                fhandle.write(f'    <programme start="{st}" stop="{et}" channel="{channel}">\n')
                fhandle.write(f'        <title lang="zh">{detail["t"]}</title>\n')
                fhandle.write('    </programme>\n')

def getChannelTVsou(fhandle, channelID):
    '''
    获取 TVSOU 的节目单和节目信息，并写入 XML 文件
    '''
    base_url = 'https://www.tvsou.com'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
        'Referer': base_url
    }
    session = requests.Session()

    for channel in channelID:
        api_url = f'{base_url}/epg/{channel}/'
        try:
            response = session.get(api_url, headers=headers, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"请求失败: {e}")
            continue

        tree = html.fromstring(response.text)
        channel_name = tree.xpath('/html/body/div[3]/div[2]/span[2]/text()')[0].strip()
        epg_names = tree.xpath('/html/body/div[3]/div[3]/div[3]/div[2]/div[2]/div[2]/ol/li/@data-name')
        epg_times = tree.xpath('/html/body/div[3]/div[3]/div[3]/div[2]/div[2]/div[2]/ol/li/@data-mainstars')

        # 写入频道信息
        fhandle.write(f'    <channel id="{channel}">\n')
        fhandle.write(f'        <display-name lang="cn">{channel_name}</display-name>\n')
        fhandle.write('    </channel>\n')

        # 写入节目信息
        for name, time_range in zip(epg_names, epg_times):
            start_time, end_time = time_range.split('-')
            start_time = datetime.now(tz).strftime('%Y%m%d') + start_time.replace(':', '')
            end_time = datetime.now(tz).strftime('%Y%m%d') + end_time.replace(':', '')
            fhandle.write(f'    <programme start="{start_time}" stop="{end_time}" channel="{channel}">\n')
            fhandle.write(f'        <title lang="cn">{name.strip()}</title>\n')
            fhandle.write('    </programme>\n')

# 主逻辑
with open('guide.xml', 'w', encoding='utf-8') as fhandle:
    fhandle.write('<?xml version="1.0" encoding="utf-8" ?>\n')
    fhandle.write('<tv generator-info-name="lxxcp" generator-info-url="https://github.com/lxxcp/epg">\n')

    # 爬取 TVSOU 节目单
    getChannelTVsou(fhandle, cctv_channel_tvsou)
    getChannelTVsou(fhandle, sat_channel_tvsou)

    # 爬取 CNTV 节目单
    getChannelCNTV(fhandle, cctv_channel)
    getChannelCNTV(fhandle, sat_channel)
    getChannelEPG(fhandle, cctv_channel)
    getChannelEPG(fhandle, sat_channel)

    fhandle.write('</tv>')