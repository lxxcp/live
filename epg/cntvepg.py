# -*- coding: utf-8 -*-
import re
import pytz
import requests
import gzip
from lxml import html
from datetime import datetime, timezone, timedelta

tz = pytz.timezone('Asia/Shanghai')

cctv_channel = ['cctv1', 'cctv2', 'cctv3', 'cctv4', 'cctv5', 'cctv5plus', 'cctv6', 
                'cctv7', 'cctv8', 'cctvjilu', 'cctv10', 'cctv11', 'cctv12', 'cctvchild', 
                'cctv15', 'cctv16', 'cctv17', 'cctveurope', 'cctvamerica', 'cctvxiyu', 'cctv4k', 'cctvarabic', 
                'cctvfrench', 'cctvrussian', 'shijiedili', 'dianshigouwu', 'taiqiu', 'jingpin', 'shishang', 'hjjc', 
                'zhinan', 'diyijuchang', 'fyjc', 'cctvfyzq', 'fyyy', 'cctvgaowang', 'xianfengjilu','cetv1', 'cetv2', 'cetv3', 'cetv4'] 

def getChannelCNTV(fhandle, channelID):
    # change channelID list to str cids
    cids = ''
    for x in channelID:
        cids = cids + x + ','
    date = '%Y%m%d'
    epgdate = datetime.now(tz).strftime(date)
    session = requests.Session()
    api = f"http://api.cntv.cn/epg/epginfo?c={cids}&d={epgdate}"
    epgdata = session.get(api).json()

    for n in range(len(channelID)):
        # channelName = epgdata[channelID[n]]['channelName']
        fhandle.write(f'\t<channel id="{channelID[n]}">\n')
        fhandle.write(f'\t\t <display-name lang="cn">{epgdata[channelID[n]]["channelName"]}</display-name>\n')
        fhandle.write('\t</channel>\n')


def getChannelEPG(fhandle, channelID):
    date = '%Y%m%d'
    epgdate = [
        datetime.now(tz).strftime(date),                         # 当天
        (datetime.now(tz) + timedelta(days=1)).strftime(date),   # 后一天
        (datetime.now(tz) + timedelta(days=2)).strftime(date),   # 后两天
        (datetime.now(tz) + timedelta(days=3)).strftime(date),   # 后三天
        (datetime.now(tz) + timedelta(days=4)).strftime(date),   # 后四天
    ]

    cids = ''
    for x in channelID:
        cids = cids + x + ','

    for k in epgdate:
        session = requests.Session()
        api = f"http://api.cntv.cn/epg/epginfo?c={cids}&d={k}"
        epgdata = session.get(api).json()
        for n in range(len(channelID)):
            name = epgdata[channelID[n]]['channelName']
            program = epgdata[channelID[n]]['program']
            for detail in program:
                # write programme
                st = datetime.fromtimestamp(detail['st']).strftime('%Y%m%d%H%M') + '00'
                et = datetime.fromtimestamp(detail['et']).strftime('%Y%m%d%H%M') + '00'

                fhandle.write(f'\t<programme start="{st} +0800" stop="{et} +0800" channel="{channelID[n]}">\n')
                fhandle.write(f'\t\t<title lang="zh">{detail["t"]}</title>\n')
                fhandle.write(f'\t\t<desc lang="zh"></desc>\n')
                fhandle.write('\t</programme>\n')

def getsave():
    # 使用 gzip 打开文件进行压缩
    with gzip.open('cntvepg.xml.gz', 'wt', encoding='utf-8') as fhandle:
        fhandle.write('<?xml version="1.0" encoding="utf-8" ?>\n')
        fhandle.write('<tv generator-info-name="xiaoluoxxx" generator-info-url="https://github.com/xiaoluoxxx/iptv-one">\n')
        getChannelCNTV(fhandle, cctv_channel)
       # getChannelCNTV(fhandle, sat_channel)
        getChannelEPG(fhandle, cctv_channel)
       # getChannelEPG(fhandle, sat_channel)
        fhandle.write('</tv>')

if __name__ == '__main__':
    getsave()
    print('获取完成！')