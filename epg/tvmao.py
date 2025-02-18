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
 
 
def get_program_info(link, sublink, week_day, epg_file_name): 
    """获取节目信息并写入文件""" 
    with open(epg_file_name, "a+", encoding="utf-8") as f: 
        date_str = time.strftime("%Y/%m/%d  %A", time.localtime(time.time()  + (week_day - int(time.strftime("%w")))  * 24 * 3600)) 
        f.write(date_str)  
        f.write("\n\n")  
 
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
        with open(epg_file_name, "a+", encoding="utf-8") as f: 
            for tagprogram in list_program_div: 
                try: 
                    if is_valid_date(tagprogram.text):  
                        f.write(tagprogram.text)  
                        f.write("    ") 
                    elif tagprogram.text!=  '正在播出': 
                        f.write(tagprogram.text)  
                        f.write("\n")  
                except: 
                    continue 
 
        list_first_form = soup.find(name='form')  
        if list_first_form and list_first_form.get("a")  and list_first_form.get("q")  and list_first_form.find("button"):  
            sublink = f"/api/pg?p={sub_req(list_first_form['a'], list_first_form['q'], list_first_form.button['id'])}"  
            website = f'{link}{sublink}' 
            sub_r = requests.get(website)  
            soup = BeautifulSoup(sub_r.json()[1],  'lxml') 
            list_program_div = soup.find_all(name='span')  
            with open(epg_file_name, "a+", encoding="utf-8") as f: 
                for tagprogram in list_program_div: 
                    try: 
                        if is_valid_date(tagprogram.text):  
                            f.write(tagprogram.text)  
                            f.write("    ") 
                        elif tagprogram.text!=  '正在播出': 
                            f.write(tagprogram.text)  
                            f.write("\n")  
                    except: 
                        continue 
                f.write("\n\n")  
    except Exception as e: 
        print(f"Error getting program info: {e}") 
 
 
def get_program(link, sublink, week_day, epg_file_name): 
    """调用获取节目信息的函数""" 
    get_program_info(link, sublink, week_day, epg_file_name) 
 
 
def main(): 
    link = "https://www.tvmao.com"  
 
    # 中央电视台 
    CCTV_prog = ['CCTV1', 'CCTV2', 'CCTV3', 'CCTV4', 'CCTV5', 'CCTV6'] 
    epg_path = 'epg/cctv/' 
    if not os.path.exists(epg_path):  
        os.makedirs(epg_path)  
    for prog in CCTV_prog: 
        epg_name = epg_path + prog + '.txt' 
        with open(epg_name, "w+", encoding="utf-8") as f: 
            f.write("")  
        print(prog) 
        for num in range(1, 8): 
            sublink = f"/program/CCTV-{prog}-w{num}.html" 
            get_program(link, sublink, num, epg_name) 
 
    # 省级电视台 
    province_prog = ['AHTV1', 'BTV1', 'CCQTV1', 'FJTV2', 'XMTV5', 'HUNANTV1'] 
    epg_path = 'epg/province/' 
    if not os.path.exists(epg_path):  
        os.makedirs(epg_path)  
    for prog in province_prog: 
        epg_name = epg_path + prog + '.txt' 
        with open(epg_name, "w+", encoding="utf-8") as f: 
            f.write("")  
        print(prog) 
        for num in range(1, 8): 
            sublink = f"/program_satellite/{prog}-w{num}.html" 
            get_program(link, sublink, num, epg_name) 
 
 
if __name__ == "__main__": 
    main() 
 