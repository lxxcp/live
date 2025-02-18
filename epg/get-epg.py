# -*- coding: utf-8 -*- 
import re 
import pytz 
import requests 
import gzip  # 导入 gzip 模块 
from lxml import html 
from datetime import datetime, timezone, timedelta 
 
tz = pytz.timezone('Asia/Shanghai')   
 
cctv_channel = ['cctv1', 'cctv2', 'cctv3', 'cctv4', 'cctv5', 'cctv5plus', 'cctv6', 
                'cctv7', 'cctv8', 'cctvjilu', 'cctv10', 'cctv11', 'cctv12', 'cctvchild', 
                'cctv15', 'cctv16', 'cctv17', 'cctveurope','cctvamerica','cctvxiyu','cctv4k',
                'cctvarabic','cctvfrench','cctvrussian','shijiedili','dianshigouwu','taiqiu','jingpin','shishang','hjjc',zhinan','diyijuchang','fyjc','cctvfyzq','fyyy','cctvgaowang','fyjc'] 
cctv_channel_tvsou = ['cctv-1', 'cctv-2', 'cctv-3', 'cctv-4', 'cctv-5', 'cctv5+', 'cctv-6', 
                      'cctv-7', 'cctv-8', 'cctv-9', 'cctv-10', 'cctv-11', 'cctv-12'] 
 
sat_channel = ['cetv1', 'cetv2', 'cetv3', 'cetv4', 'btv1', 'btvjishi', 'dongfang', 
               'hunan', 'shandong', 'zhejiang', 'jiangsu', 'guangdong', 'dongnan', 'anhui', 
               'gansu', 'liaoning', 'travel', 'neimenggu', 'ningxia', 'qinghai', 'xiamen', 
               'yunnan', 'chongqing', 'jiangxi', 'shan1xi', 'shan3xi', 'shenzhen', 'sichuan', 'tianjin', 
               'guangxi', 'guizhou', 'hebei', 'henan', 'heilongjiang', 'hubei', 'jilin', 
               'yanbian', 'xizang', 'xinjiang', 'bingtuan', 'btvchild', 'gaoerfu', 'sdetv', 'xianggangweishi',
 'shuhua', 'kuailechuidiao', 'cctvliyuan', 'wushushijie', 'cctvqimo', 'huanqiuqiguan', 'cctvzhengquanzixun', 'btvchild', 'youxijingji'] 
sat_channel_tvsou = ['hubei', 'hunan', 'zhejiang', 'jiangsu', 'dongfang', 'btv1', 'guangdong', 
                      'shenzhen', 'heilongjiang', 'tianjin', 'shandong', 'anhui', 'liaoning'] 
 
 
def get_epg_data(session, cids, epgdate): 
    try: 
        api = f"http://api.cntv.cn/epg/epginfo?c={cids}&d={epgdate}"   
        return session.get(api).json()   
    except requests.RequestException as e: 
        print(f"Request error: {e}") 
        return {} 
    except ValueError as e: 
        print(f"JSON decoding error: {e}") 
        return {} 
 
 
def getChannelCNTV(fhandle, channelID): 
    ''' 
    通过央视cntv接口，获取央视，和上星卫视的节目单，写入同目录下 guide.xml   文件，文件格式符合xmltv标准 
    接口返回的json转换成dict后类似如下 
    {'cctv1': {'isLive': '九九第1集', 'liveSt': 1535264130, 'channelName': 'CCTV-1 综合', 'program': [{'t': '生活提示2018-187', 'st': 1535215320, 'et': 1535215680, 'showTime': '00:42', 'eventType': '', 'eventId': '', 'duration': 360}]}} 
 
    Args: 
        fhandle,文件处理对象，用于后续调用，直接写入xml文件 
        channelID,电视台列表，list格式，可以批量一次性获取多个节目单 
 
    Return: 
        None,直接写入xml文件 
    ''' 
    cids = ','.join(channelID) 
    epgdate = datetime.now(tz).strftime('%Y%m%d')   
    session = requests.Session() 
    epgdata = get_epg_data(session, cids, epgdate) 
 
    for channel in channelID: 
        if channel in epgdata: 
            # write channel id info 
            fhandle.write(f'      <channel id="{channel}">\n') 
            fhandle.write(f'          <display-name lang="cn">{epgdata[channel]["channelName"]}</display-name>\n') 
            fhandle.write('      </channel>\n') 
 
 
def getChannelEPG(fhandle, channelID): 
    cids = ','.join(channelID) 
    session = requests.Session() 
    today = datetime.now(tz)   
    dates = [today + timedelta(days=i) for i in range(4)] 
    epgdates = [date.strftime('%Y%m%d') for date in dates] 
 
    all_epg_data = [get_epg_data(session, cids, epgdate) for epgdate in epgdates] 
 
    for channel in channelID: 
        for epgdata_current in all_epg_data: 
            if channel in epgdata_current: 
                program = epgdata_current[channel]['program'] 
                for detail in program: 
                    # 处理 start 和 stop 时间戳 
                    st = datetime.fromtimestamp(detail['st']).astimezone(tz).strftime('%Y%m%d%H%M%S  %z') 
                    et = datetime.fromtimestamp(detail['et']).astimezone(tz).strftime('%Y%m%d%H%M%S  %z') 
                    # 写入 programme 
                    fhandle.write(f'       <programme  channel="{channel}" start="{st}" stop="{et}" >\n') 
                    fhandle.write(f'           <title lang="zh">{detail["t"]}</title>\n') 
                    fhandle.write('       </programme>\n') 
 
 
# 使用 gzip 打开文件进行压缩写入 
with gzip.open('guide.xml.gz',  'wt', encoding='utf-8') as fhandle: 
    fhandle.write('<?xml   version="1.0" encoding="utf-8"?>\n') 
    fhandle.write('<tv   generator-info-name="lxxcp" generator-info-url="https://github.com/lxxcp/epg">\n')   
    getChannelCNTV(fhandle, cctv_channel) 
    getChannelCNTV(fhandle, sat_channel) 
    getChannelEPG(fhandle, cctv_channel) 
    getChannelEPG(fhandle, sat_channel) 
    fhandle.write('</tv>')  
