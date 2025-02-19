import re 
import pytz 
import requests 
import gzip 
from lxml import html 
from datetime import datetime, timezone, timedelta 
import random 
import time 
 
# 设置时区为亚洲上海 
tz = pytz.timezone('Asia/Shanghai')  

# 定义央视频道列表 
cctv_channel = ['cctv1', 'cctv2', 'cctv3', 'cctv4', 'cctv5', 'cctv5plus', 'cctv6', 
                'cctv7', 'cctv8', 'cctvjilu', 'cctv10', 'cctv11', 'cctv12','cctv13', 'cctvchild', 
                'cctv15', 'cctv16', 'cctv17', 'cctveurope', 'cctvamerica', 'cctv4k'] 
 
# 定义上星卫视频道列表 
sat_channel = ['cetv1', 'cetv2', 'cetv4','btv1', 'btvjishi', 'dongfang', 'hunan', 'shandong', 'zhejiang', 'jiangsu', 'guangdong', 'dongnan', 'anhui', 
               'gansu', 'liaoning', 'travel', 'neimenggu', 'ningxia', 'qinghai', 'xiamen', 
               'yunnan', 'chongqing', 'jiangxi', 'shan1xi', 'shan3xi', 'shenzhen', 'sichuan', 'tianjin', 
               'guangxi', 'guizhou', 'hebei', 'henan', 'heilongjiang', 'hubei', 'jilin', 
               'yanbian', 'xizang', 'xinjiang', 'bingtuan', 'sdetv'] 

#'xianfengjilu', 'btvchild', 'cetv1', 'cetv2', 'cetv4','shuhua', 'kuailechuidiao', 'cctvliyuan', 'wushushijie', 'cctvqimo', 'huanqiuqiguan', 'cctvzhengquanzixun', 'youxijingji', 'cetv3', 'xianggangweishi''cctvarabic', 'cctvxiyu', 'cctvfrench', 'cctvrussian', 
#, 'shijiedili', 'dianshigouwu', 'taiqiu', 'jingpin', 'shishang', 'hjjc','zhinan', 'diyijuchang', 'fyjc', 'cctvfyzq', 'fyyy', 'cctvgaowang'
# 模拟不同浏览器的请求头 
user_agents = [ 
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', 
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36', 
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0', 
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15' 
] 
 
 
def get_epg_data(session, cids, epgdate): 
    """ 
    向API发送请求获取节目单数据 
    :param session: requests会话对象 
    :param cids: 频道ID列表，用逗号连接 
    :param epgdate: 日期，格式为YYYYMMDD 
    :return: 解析后的JSON数据或空字典 
    """ 
    try: 
        # 正确格式化API地址 
        api = f"http://api.cntv.cn/epg/epginfo?c={cids}&d={epgdate}"  
        # 随机选择一个请求头 
        headers = { 
            'User-Agent': random.choice(user_agents)  
        } 
        response = session.get(api,  headers=headers) 
        response.raise_for_status()   # 检查请求是否成功 
        epgdata = response.json()  
        print(f"API response for {cids} on {epgdate}: {epgdata}") 
        return epgdata 
    except requests.RequestException as e: 
        print(f"Request error: {e}") 
        return {} 
    except ValueError as e: 
        print(f"JSON decoding error: {e}") 
        return {} 
 
 
def get_channel_info(fhandle, channel_id, epg_data): 
    """ 
    将频道信息写入XML文件 
    :param fhandle: 文件处理对象 
    :param channel_id: 频道ID 
    :param epg_data: 节目单数据 
    """ 
    if channel_id in epg_data: 
        channel_name = epg_data[channel_id].get("channelName", channel_id) 
        fhandle.write(f'     <channel id="{channel_id}">\n') 
        fhandle.write(f'         <display-name lang="cn">{channel_name}</display-name>\n') 
        fhandle.write('     </channel>\n') 
 
 
def get_channel_programs(fhandle, channel_id, all_epg_data): 
    """ 
    将节目信息写入XML文件 
    :param fhandle: 文件处理对象 
    :param channel_id: 频道ID 
    :param all_epg_data: 多日的节目单数据列表 
    """ 
    for epg_data in all_epg_data: 
        if channel_id in epg_data: 
            programs = epg_data[channel_id].get('program', []) 
            for program in programs: 
                start_time = datetime.fromtimestamp(program['st']).astimezone(tz).strftime('%Y%m%d%H%M%S  %z') 
                end_time = datetime.fromtimestamp(program['et']).astimezone(tz).strftime('%Y%m%d%H%M%S  %z') 
                title = program.get('t',  "Unknown Program") 
                fhandle.write(f'     <programme channel="{channel_id}" start="{start_time}" stop="{end_time}">\n') 
                fhandle.write(f'         <title lang="zh">{title}</title>\n') 
                fhandle.write('     </programme>\n') 
 
 
def main(): 
    """ 
    主函数，包含整个流程的调度  
    """ 
    with gzip.open('guide.xml.gz',  'wt', encoding='utf-8') as fhandle: 
        fhandle.write('<?xml  version="1.0" encoding="utf-8"?>\n') 
        fhandle.write('<tv  generator-info-name="lxxcp" generator-info-url="https://github.com/lxxcp/epg">\n')  
 
        session = requests.Session() 
        all_channels = cctv_channel+ sat_channel 
        today = datetime.now(tz)  
        dates = [today + timedelta(days=i) for i in range(4)] 
        epg_dates = [date.strftime('%Y%m%d') for date in dates] 
 
        all_channel_epg_data = [] 
        # 为所有频道获取多日的节目单数据 
        for epg_date in epg_dates: 
            cids = ','.join(all_channels) 
            epg_data = get_epg_data(session, cids, epg_date) 
            all_channel_epg_data.append(epg_data)  
            # 随机设置请求间隔 
            time.sleep(random.uniform(1,  3)) 
 
        # 写入频道信息 
        for channel in all_channels: 
            get_channel_info(fhandle, channel, all_channel_epg_data[0]) 
 
        # 写入节目信息 
        for channel in all_channels: 
            get_channel_programs(fhandle, channel, all_channel_epg_data) 
 
        fhandle.write('</tv>')  
 
 
if __name__ == "__main__": 
    main() 
 
