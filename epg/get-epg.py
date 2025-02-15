# -*- coding: utf-8 -*-
import re
import pytz
import requests
from lxml import html
from datetime import datetime, timezone, timedelta

# 设置时区
tz = pytz.timezone('Asia/Shanghai')

# 频道列表
cctv_channel = [
    'cctv1', 'cctv2', 'cctv3', 'cctv4', 'cctv5', 'cctv5plus', 'cctv6',
    'cctv7', 'cctv8', 'cctvjilu', 'cctv10', 'cctv11', 'cctv12', 'cctvchild',
    'cctv15', 'cctv16', 'cctv17', 'cctv4k'
]
cctv_channel_tvsou = [
    'cctv-1', 'cctv-2', 'cctv-3', 'cctv-4', 'cctv-5', 'cctv5+', 'cctv-6',
    'cctv-7', 'cctv-8', 'cctv-9', 'cctv-10', 'cctv-11', 'cctv-12'
]

sat_channel = [
    'cetv1', 'cetv2', 'cetv3', 'cetv4', 'btv1', 'btvjishi', 'dongfang',
    'hunan', 'shandong', 'zhejiang', 'jiangsu', 'guangdong', 'dongnan', 'anhui',
    'gansu', 'liaoning', 'travel', 'neimenggu', 'ningxia', 'qinghai', 'xiamen',
    'yunnan', 'chongqing', 'jiangxi', 'shan1xi', 'shan3xi', 'shenzhen', 'sichuan', 'tianjin',
    'guangxi', 'guizhou', 'hebei', 'henan', 'heilongjiang', 'hubei', 'jilin',
    'yanbian', 'xizang', 'xinjiang', 'bingtuan', 'btvchild', 'gaoerfu', 'sdetv'
]
sat_channel_tvsou = [
    'hubei', 'hunan', 'zhejiang', 'jiangsu', 'dongfang', 'btv1', 'guangdong',
    'shenzhen', 'heilongjiang', 'tianjin', 'shandong', 'anhui', 'liaoning'
]
# 频道名称映射字典
channel_name_mapping = {
    'cctv1': 'CCTV-1 综合',
    'cctv2': 'CCTV-2 财经',
    'cctv3': 'CCTV-3 综艺',
    'cctv4': 'CCTV-4 中文国际',
    'cctv5': 'CCTV-5 体育',
    'cctv5plus': 'CCTV-5+ 体育赛事',
    'cctv6': 'CCTV-6 电影',
    'cctv7': 'CCTV-7 国防军事',
    'cctv8': 'CCTV-8 电视剧',
    'cctvjilu': 'CCTV-9 纪录',
    'cctv10': 'CCTV-10 科教',
    'cctv11': 'CCTV-11 戏曲',
    'cctv12': 'CCTV-12 社会与法',
    'cctvchild': 'CCTV-14 少儿',
    'cctv15': 'CCTV-15 音乐',
    'cctv16': 'CCTV-16 奥林匹克',
    'cctv17': 'CCTV-17 农业农村',
    'cctv4k': 'CCTV-4K 超高清',
}

def generate_cids(channel_ids):
    """将频道列表转换为逗号分隔的字符串"""
    return ','.join(channel_ids)

def fetch_epg_data(session, cids, date):
    """从 CNTV API 获取 EPG 数据"""
    api_url = f"http://api.cntv.cn/epg/epginfo?c={cids}&d={date}"
    try:
        response = session.get(api_url)
        response.raise_for_status()  # 检查请求是否成功
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"请求 EPG 数据失败: {e}")
        return None

def write_channel_info(fhandle, channel_id, channel_name=None):
    """写入频道信息到 XML 文件"""
    # 如果未提供 channel_name，则从映射字典中获取
    if channel_name is None:
        channel_name = channel_name_mapping.get(channel_id, channel_id)  # 如果未找到映射，则使用 channel_id

    fhandle.write(f'    <channel id="{channel_id}">\n')
    fhandle.write(f'        <display-name lang="cn">{channel_name}</display-name>\n')
    fhandle.write('    </channel>\n')

def write_program_info(fhandle, channel_id, program_title, start_time, end_time):
    """写入节目信息到 XML 文件"""
    fhandle.write(f'    <programme start="{start_time}" stop="{end_time}" channel="{channel_id}">\n')
    fhandle.write(f'        <title lang="zh">{program_title}</title>\n')
    fhandle.write('    </programme>\n')

def get_channel_cctv(fhandle, channel_ids):
    """获取央视频道 EPG 数据并写入文件"""
    cids = generate_cids(channel_ids)
    epg_date = datetime.now(tz).strftime('%Y%m%d')
    session = requests.Session()
    epg_data = fetch_epg_data(session, cids, epg_date)

    if not epg_data:
        return

    for channel_id in channel_ids:
        channel_info = epg_data.get(channel_id, {})
        if not channel_info:
            continue

        # 写入频道信息
        write_channel_info(fhandle, channel_id, channel_info.get('channelName', ''))

def get_channel_epg(fhandle, channel_ids):
    """获取频道 EPG 数据并写入文件"""
    cids = generate_cids(channel_ids)
    session = requests.Session()

    # 获取 3 天的 EPG 数据
    for day_offset in range(3):
        epg_date = (datetime.now(tz) + timedelta(days=day_offset)).strftime('%Y%m%d')
        epg_data = fetch_epg_data(session, cids, epg_date)

        if not epg_data:
            continue

        for channel_id in channel_ids:
            programs = epg_data.get(channel_id, {}).get('program', [])
            for program in programs:
                start_time = datetime.fromtimestamp(program['st']).strftime('%Y%m%d%H%M%S')
                end_time = datetime.fromtimestamp(program['et']).strftime('%Y%m%d%H%M%S')
                write_program_info(fhandle, channel_id, program['t'], start_time, end_time)

def main():
    """主函数"""
    with open('guide.xml', 'w', encoding='utf-8') as fhandle:
        fhandle.write('<?xml version="1.0" encoding="utf-8" ?>\n')
        fhandle.write('<tv generator-info-name="lxxcp" generator-info-url="https://github.com/lxxcp/epg">\n')

        # 获取央视和卫视的 EPG 数据
        get_channel_cctv(fhandle, cctv_channel)
        get_channel_cctv(fhandle, sat_channel)
        get_channel_epg(fhandle, cctv_channel)
        get_channel_epg(fhandle, sat_channel)

        fhandle.write('</tv>\n')

if __name__ == '__main__':
    main()
