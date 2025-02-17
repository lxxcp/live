import os 
import gzip 
import xml.etree.ElementTree  as ET 
import requests 
import logging 
from copy import deepcopy 
import datetime 
import pytz 
 
# 配置参数 
config_file = os.path.join(os.path.dirname(__file__),  'config.txt')  
epg_match_file = os.path.join(os.path.dirname(__file__),  'epg_match.xml')  
output_file_gz = os.path.join(os.path.dirname(os.path.dirname(__file__)),  'e.xml.gz')  
TIMEZONE = pytz.timezone('Asia/Shanghai')  
 
 
def load_config(config_file): 
    """加载有效频道ID""" 
    tvg_ids = {} 
    try: 
        with open(config_file, 'r') as file: 
            tvg_ids = {line.strip():  line.strip()  for line in file if line.strip()}  
        logging.info(f" 已加载 {len(tvg_ids)} 个频道ID从 {config_file}") 
    except Exception as e: 
        logging.error(f" 读取配置文件失败 {config_file}: {e}") 
    return tvg_ids 
 
 
def load_epg_mapping(epg_match_file): 
    """加载频道名称映射表""" 
    mapping = {} 
    try: 
        tree = ET.parse(epg_match_file)  
        for epg in tree.findall('epg'):  
            epgid = epg.find('epgid').text  
            names = epg.find('name').text.split(',')  
            for name in names: 
                mapping[name.strip()] = epgid 
        logging.info(f" 已加载 {len(mapping)} 个频道映射从 {epg_match_file}") 
    except Exception as e: 
        logging.error(f" 加载映射文件失败 {epg_match_file}: {e}") 
    return mapping 
 
 
def normalize_channel_name(name, mapping, tvg_ids): 
    original_name = name 
    norm_id = mapping.get(name,  name) 
    if norm_id not in tvg_ids: 
        logging.debug(f" 频道未匹配: 原名 '{original_name}', 映射后 '{norm_id}' 不在配置ID中") 
    return norm_id if norm_id in tvg_ids else original_name 
 
 
def fetch_and_extract_xml(url): 
    try: 
        logging.info(f" 正在获取数据: {url}") 
        response = requests.get(url,  timeout=20) 
        response.raise_for_status()  
 
        # 处理压缩内容 
        if response.headers.get('Content-Encoding')  == 'gzip' or url.endswith('.gz'):  
            content = gzip.decompress(response.content)  
        else: 
            content = response.content  
 
        return ET.fromstring(content)  
    except Exception as e: 
        logging.error(f" 处理 {url} 失败: {str(e)}") 
    return None 
 
 
def parse_epg_time(start_time): 
    """解析EPG时间并转换为中国时区""" 
    if not start_time: 
        return None 
    try: 
        # 统一处理时间格式（兼容带时区和不带时区的情况） 
        dt = datetime.datetime.strptime(start_time[:14],  "%Y%m%d%H%M%S") 
        if len(start_time) > 14: 
            tz_info = start_time[14:] 
            if tz_info.upper()  == 'Z': 
                dt = dt.replace(tzinfo=pytz.utc)  
            else: 
                dt = dt.astimezone(TIMEZONE)  
        else: 
            dt = TIMEZONE.localize(dt)  
        return dt 
    except Exception as e: 
        logging.error(f" 时间解析失败 '{start_time}': {e}") 
        return None 
 
 
def filter_and_build_epg(urls, mapping, tvg_ids): 
    valid_ids = set(tvg_ids.keys())  
    root = ET.Element('tv') 
    processed_channels = set() 
 
    # 获取当天零点时间 
    now = datetime.datetime.now(TIMEZONE)  
    today_start = now.replace(hour=0,  minute=0, second=0, microsecond=0) 
    # 设置未来几天的时间范围（例如未来3天） 
    future_end = today_start + datetime.timedelta(days=3)   # 不包含 today_start 当天，包含未来3天 
 
    for url in urls: 
        epg_data = fetch_and_extract_xml(url) 
        if epg_data is None: 
            continue 
 
        # 处理频道 
        for channel in epg_data.findall('channel'):  
            tvg_id = channel.get('id')  
            if not tvg_id: 
                continue 
            norm_id = normalize_channel_name(tvg_id, mapping, tvg_ids) 
            if norm_id in valid_ids and norm_id not in processed_channels: 
                # 清理旧显示名称并添加标准化名称 
                for elem in channel.findall('display-name'):  
                    channel.remove(elem)  
                ET.SubElement(channel, 'display-name', {'lang': 'zh'}).text = norm_id 
                channel.set('id',  norm_id) 
                root.append(deepcopy(channel))  
                processed_channels.add(norm_id)  
 
        # 处理节目 
        program_count = 0 
        for program in epg_data.findall('programme'):  
            tvg_id = program.get('channel')  
            if not tvg_id: 
                continue 
            norm_id = normalize_channel_name(tvg_id, mapping, tvg_ids) 
            if norm_id not in valid_ids: 
                continue 
 
            start_time = parse_epg_time(program.get('start'))  
            if not start_time: 
                continue 
 
            # 过滤掉早于今天零点或晚于未来几天的节目 
            if start_time < today_start or start_time >= future_end: 
                continue 
 
            # 克隆并更新节目信息 
            prog = deepcopy(program) 
            prog.set('channel',  norm_id) 
            root.append(prog)  
            program_count += 1 
 
        logging.info(f" 从 {url} 添加 {program_count} 个节目") 
 
    # 处理 XML 声明时，确保格式正确 
    xml_string = ET.tostring(root,  encoding='utf-8', method='xml') 
    xml_header = b'<?xml version="1.0" encoding="utf-8"?>' 
    xml_with_header = xml_header + xml_string 
 
    # 保存最终文件 
    try: 
        with gzip.open(output_file_gz,  'wb') as f: 
            f.write(xml_with_header)  
        logging.info(f"EPG 文件已压缩保存至 {output_file_gz}") 
    except Exception as e: 
        logging.error(f" 文件保存失败: {e}") 
 
 
urls = [ 
    'https://raw.githubusercontent.com/sparkssssssssss/epg/main/pp.xml.gz',  
    'https://raw.githubusercontent.com/lxxcp/live/main/guide.xml.gz',  
    'https://epg.pw/xmltv/epg_CN.xml.gz',  
    'https://gitee.com/taksssss/tv/raw/main/epg/112114.xml.gz',  
    'https://gitee.com/taksssss/tv/raw/main/epg/51zmt.xml.gz',  
    'https://e.erw.cc/all.xml.gz',  
    'https://e.erw.cc/allcc.xml.gz',  
] 
 
if __name__ == "__main__": 
    logging.basicConfig(  
        level=logging.INFO, 
        format='%(asctime)s - %(levelname)s - %(message)s', 
        datefmt='%Y-%m-%d %H:%M:%S' 
    ) 
    channel_mapping = load_epg_mapping(epg_match_file) 
    tvg_id_list = load_config(config_file) 
    filter_and_build_epg(urls, channel_mapping, tvg_id_list) 
 
 