import requests 
import time 
import datetime 
import re 
import gzip 
from bs4 import BeautifulSoup as bs 
 
headers = { 
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,/;q=0.8,application/signed-exchange;v=b3;q=0.9", 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36", 
} 
 
def get_channels_tvmao(): 
    url_sort = "https://www.tvmao.com/program/playing/"  
    try: 
        res = requests.get(url_sort,  headers=headers, timeout=5) 
        res.raise_for_status()  
        res.encoding  = "utf-8" 
        # 打印返回的 HTML 内容，检查结构和格式 
        print(res.text)  
        soup = bs(res.text,  "html.parser")  
        provinces = {} 
        big_sorts = {} 
        channels = [] 
 
        # 使用 find_all 代替 select 
        provinces_more = soup.find_all("div",  class_="province")[0].find_all("ul", class_="province-list")[0].find_all("li") 
        big_sorts_more = soup.find_all("dl",  class_="chntypetab")[0].find_all("dd") 
 
        for province_more in provinces_more: 
            province = province_more.text.strip().replace("  黑龙", "黑龙江") 
            province_id = province_more.a["href"].replace("/program/playing/", "").replace("/", "") 
            provinces[province] = province_id 
 
        for big_sort_more in big_sorts_more: 
            sort_name = big_sort_more.text.strip()  
            url = big_sort_more.a["href"] 
            sort_id = url.replace("/program/playing/",  "").replace("/", "") 
            if sort_name in provinces or sort_name == "收藏": 
                continue 
            big_sorts[sort_name] = sort_id 
 
        sorts = {**provinces, **big_sorts} 
 
        for sort_name in sorts: 
            url = f"https://www.tvmao.com/program/playing/{sorts[sort_name]}"  
            time.sleep(0.5)  
            res = requests.get(url,  headers=headers, timeout=5) 
            res.raise_for_status()  
            res.encoding  = "utf-8" 
            soup = bs(res.text,  "html.parser")  
            channel_trs = soup.find_all("table",  class_="timetable")[0].find_all("tr") 
 
            for tr in channel_trs: 
                tr1 = tr.find("td").find("a")  
                if tr1: 
                    name = tr1["title"] 
                    href = tr1["href"] 
                    id = href.replace("/program/",  "").replace("/", "-").replace(".html", "").replace("-program_", "") 
                    # 使用原始字符串解决转义问题 
                    id = re.sub(r"-w\d$",  "", id) 
                    res1 = tr1["res"] 
                    channel = { 
                        "name": name, 
                        "id": [id], 
                        "url": f"https://m.tvmao.com/program/{id}.html",  
                        "source": "tvmao", 
                        "logo": "", 
                        "desc": "", 
                        "sort": sort_name, 
                        "res": res1, 
                    } 
                    channels.append(channel)  
    except requests.RequestException as e: 
        print(f"请求出错: {e}") 
        return [] 
    print(f"共有频道：{len(channels)}") 
    return channels 
 
def get_epgs_tvmao2(channel, channel_id, dt, func_arg): 
    epgs = [] 
    desc = "" 
    msg = "" 
    success = 1 
    ban = 0  # 标识是否被 BAN 掉了,此接口不确定是否有反爬机制 
    now_date = datetime.datetime.now().date()  
    need_date = dt 
    delta = need_date - now_date 
    now_weekday = now_date.weekday()  
    need_weekday = now_weekday + delta.days  + 1 
    id_split = channel_id.split("-")  
    if len(id_split) == 2: 
        id = id_split[1] 
    elif len(id_split) == 3: 
        id = "-".join(id_split[1:3]) 
    else: 
        id = channel_id 
    url = f"https://lighttv.tvmao.com/qa/qachannelschedule?epgCode={id}&op=getProgramByChnid&epgName=&isNew=on&day={need_weekday}"  
    try: 
        res = requests.get(url,  headers=headers) 
        res.raise_for_status()  
        res_j = res.json()  
        datas = res_j[2]["pro"] 
        for data in datas: 
            title = data["name"] 
            starttime_str = data["time"] 
            starttime = datetime.datetime.combine(  
                dt, datetime.time(int(starttime_str[:2]),  int(starttime_str[-2:])) 
            ) 
            epg = { 
                "channel_id": channel["id"][0],  # 修正为字典访问 
                "starttime": starttime, 
                "endtime": None, 
                "title": title, 
                "desc": desc, 
                "program_date": dt, 
            } 
            epgs.append(epg)  
    except (requests.RequestException, (KeyError, IndexError), ValueError) as e: 
        success = 0 
        msg = f"spider-tvmao-{e}" 
    ret = { 
        "success": success, 
        "epgs": epgs, 
        "msg": msg, 
        "last_program_date": dt, 
        "ban": 0, 
        "source": "tvmao", 
    } 
    return ret 
 
def generate_xml(channels, epgs): 
    xml = '<?xml version="1.0" encoding="UTF-8"?>\n<tv>\n' 
    for channel in channels: 
        xml += f'  <channel id="{channel["id"][0]}">\n' 
        xml += f'    <display-name>{channel["name"]}</display-name>\n' 
        xml += f'    <url>{channel["url"]}</url>\n' 
        xml += f'    <sort>{channel["sort"]}</sort>\n' 
        xml += '  </channel>\n' 
    for epg in epgs: 
        endtime_str = epg["endtime"].strftime("%Y%m%d%H%M%S") if epg["endtime"] else "" 
        xml += f'  <programme channel="{epg["channel_id"]}" start="{epg["starttime"].strftime("%Y%m%d%H%M%S")}" stop="{endtime_str}">\n' 
        xml += f'    <title>{epg["title"]}</title>\n' 
        xml += f'    <desc>{epg["desc"]}</desc>\n' 
        xml += '  </programme>\n' 
    xml += '</tv>' 
    return xml 
 
def save_xml_gz(xml, filename): 
    try: 
        with gzip.open(filename,  'wt', encoding='utf-8') as f: 
            f.write(xml)  
    except OSError as e: 
        print(f"保存文件出错: {e}") 
 
 if __name__ == "__main__": 
    main() 
 