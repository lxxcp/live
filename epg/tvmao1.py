# -*- coding: utf-8 -*-
import requests
import time
import datetime
import re
import gzip
import xml.etree.ElementTree as ET
from utils.general import headers
from bs4 import BeautifulSoup as bs
from datetime import timedelta

headers = {
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36",
}

NS = {'xmltv': 'http://xmltv.c-coding.co.uk/xmltv'}

def generate_xmltv(output_path='tvmao.xml.gz', days=7):
    """生成XMLTV格式的EPG数据并压缩为gz文件"""
    start_time = time.time()
    
    # 创建XML根节点
    root = ET.Element('tv')
    root.set('generator-info-name', 'TVmao EPG Generator')
    root.set('generator-info-url', 'https://tvmao.com')
    
    # 获取所有频道
    channels = get_channels_tvmao()
    print(f"共获取到{len(channels)}个频道")
    
    # 处理每个频道
    for idx, channel in enumerate(channels, 1):
        channel_id = channel['id'][0]
        print(f"处理频道 {idx}/{len(channels)}: {channel['name']} ({channel_id})")
        
        # 添加频道信息到XML
        channel_elem = ET.SubElement(root, 'channel', id=channel_id)
        ET.SubElement(channel_elem, 'display-name').text = channel['name']
        if channel.get('logo'):
            ET.SubElement(channel_elem, 'icon', src=channel['logo'])
        
        # 获取多天节目表
        for day in range(days):
            current_date = datetime.date.today() + timedelta(days=day)
            print(f"  获取 {current_date} 节目表...")
            
            # 获取节目数据
            epg_data = get_epgs_tvmao2(channel, channel_id, current_date, None)
            if not epg_data['success']:
                print(f"  获取失败: {epg_data['msg']}")
                continue
                
            # 添加节目信息到XML
            for program in epg_data['epgs']:
                programme_elem = ET.SubElement(
                    root, 
                    'programme',
                    start=format_time(program['starttime']),
                    stop=format_time(program.get('endtime')),  # 需要补充结束时间逻辑
                    channel=channel_id
                )
                ET.SubElement(programme_elem, 'title').text = program['title']
                if program['desc']:
                    ET.SubElement(programme_elem, 'desc').text = program['desc']

    # 生成XML文件
    tree = ET.ElementTree(root)
    
    # 压缩为gz文件
    with gzip.open(output_path, 'wb') as f:
        tree.write(f, encoding='utf-8', xml_declaration=True)
    
    print(f"生成完成！耗时 {time.time()-start_time:.2f} 秒")
    print(f"文件已保存至：{output_path}")

def format_time(dt):
    """格式化时间为XMLTV标准格式"""
    return dt.strftime('%Y%m%d%H%M%S +0800') if dt else ''

# 原有获取频道和节目数据的函数（保持原样）
def get_channels_tvmao():
    # 原有实现...
    pass

def get_epgs_tvmao2(channel, channel_id, dt, func_arg):
    # 原有实现...
    pass

if __name__ == '__main__':
    generate_xmltv(days=3)  # 生成3天节目表
