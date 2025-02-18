#!/usr/bin/python 
# coding: utf-8 
import urllib3 
import requests 
import datetime 
import time 
import base64 
import ssl 
import json 
from bs4 import BeautifulSoup 
import os 
import xml.etree.ElementTree  as ET 
import gzip 
 
 
def is_valid_date(strdate): 
    """检查字符串是否为有效的时间格式（HH:MM）""" 
    try: 
        if ":" in strdate: 
            time.strptime(strdate,  "%H:%M") 
            return True 
        return False 
    except: 
        return False 
 
 
def sub_req(a, q, id): 
    """生成请求参数""" 
    _keyStr = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=" 
    str1 = "|" + q 
    v = base64.b64encode(str1.encode('utf-8'))  
    str2 = id + "|" + a 
    w = base64.b64encode(str2.encode('utf-8'))  
    str3 = time.strftime("%w")  
    wday = 7 if int(str3) == 0 else int(str3) 
    F = _keyStr[wday * wday] 
    return F + str(w, 'utf-8') + str(v, 'utf-8') 
 
 
def get_program_info(link, sublink, week_day): 
    """获取节目信息""" 
    date_str = time.strftime("%Y%m%d",  time.localtime(time.time()  + (week_day - int(time.strftime("%w")))  * 24 * 3600)) 
    headers = { 
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; Win64; x64; rv:59.0) Gecko/20100101 Firefox/59.0', 
        'Connection': 'keep-alive', 
        'Cache-Control': 'no-cache' 
    } 
    website = f'{link}{sublink}' 
 
    try: 
        r = requests.get(website,  headers=headers) 
        soup = BeautifulSoup(r.text,  'lxml') 
 
        # 获取节目列表 
        list_program_div = soup.find(name='div',  attrs={"class": "epg"}).find_all(name='span') 
        programs = [] 
        current_time = "" 
        for tagprogram in list_program_div: 
            try: 
                if is_valid_date(tagprogram.text):  
                    current_time = tagprogram.text  
                elif tagprogram.text!=  '正在播出': 
                    programs.append((current_time,  tagprogram.text))  
            except: 
                continue 
 
        list_first_form = soup.find(name='form')  
        if list_first_form and list_first_form.get("a")  and list_first_form.get("q")  and list_first_form.find("button"):  
            sublink = f"/api/pg?p={sub_req(list_first_form['a'], list_first_form['q'], list_first_form.button['id'])}"  
            website = f'{link}{sublink}' 
            sub_r = requests.get(website)  
            soup = BeautifulSoup(sub_r.json()[1],  'lxml') 
            list_program_div = soup.find_all(name='span')  
            current_time = "" 
            for tagprogram in list_program_div: 
                try: 
                    if is_valid_date(tagprogram.text):  
                        current_time = tagprogram.text  
                    elif tagprogram.text!=  '正在播出': 
                        programs.append((current_time,  tagprogram.text))  
                except: 
                    continue 
        return programs, date_str 
    except Exception as e: 
        print(f"Error getting program info: {e}") 
        return [], "" 
 
 
def get_program(link, sublink, week_day): 
    """调用获取节目信息的函数""" 
    return get_program_info(link, sublink, week_day) 
 
 
def generate_xml(link): 
    # 中央电视台 
    CCTV_prog = ['CCTV1', 'CCTV2', 'CCTV3', 'CCTV4', 'CCTV5', 'CCTV6'] 
    # 省级电视台 
    province_prog = ['AHTV1', 'BTV1', 'CCQTV1', 'FJTV2', 'XMTV5', 'HUNANTV1'] 
    # 创建 XML 根元素 
    tv = ET.Element('tv') 
 
    for prog_list in [CCTV_prog, province_prog]: 
        for prog in prog_list: 
            channel = ET.SubElement(tv, 'channel', id=prog) 
            display_name = ET.SubElement(channel, 'display-name') 
            display_name.text  = prog 
            for num in range(1, 8): 
                if prog_list is CCTV_prog: 
                    sublink = f"/program/CCTV-{prog}-w{num}.html" 
                else: 
                    sublink = f"/program_satellite/{prog}-w{num}.html" 
                programs, date_str = get_program(link, sublink, num) 
                for time_str, program_title in programs: 
                    start_time = f"{date_str}{time_str.replace(':',  '')} +0800" 
                    end_hour = int(time_str.split(':')[0])  + 1 
                    if end_hour >= 24: 
                        end_date = (datetime.datetime.strptime(date_str,  "%Y%m%d") + datetime.timedelta(days=1)).strftime(  
                            "%Y%m%d") 
                        end_hour = end_hour - 24 
                    else: 
                        end_date = date_str 
                    end_time = f"{end_date}{str(end_hour).zfill(2)}{time_str.split(':')[1]}  +0800" 
                    program = ET.SubElement(tv, 'programme', start=start_time, stop=end_time, channel=prog) 
                    title = ET.SubElement(program, 'title', lang='zh') 
                    title.text  = program_title 
 
    xml_str = ET.tostring(tv,  encoding='utf-8') 
    with gzip.open('tvmao.xml.gz',  'wb') as f: 
        f.write(xml_str)  
 
 
def main(): 
    link = "https://www.tvmao.com"  
    generate_xml(link) 
 
 
if __name__ == "__main__": 
    main() 
 