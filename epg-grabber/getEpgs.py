import os 
import gzip 
import xml.etree.ElementTree  as ET 
import requests 
import logging 
from copy import deepcopy 
import datetime 
import pytz 
 
# 配置参数 
save_as_gz = True 
config_file = os.path.join(os.path.dirname(__file__),  'config.txt')  
epg_match_file = os.path.join(os.path.dirname(__file__),  'epg_match.xml')  
output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)),  'e.xml')  
output_file_gz = output_file + '.gz' 
TIMEZONE = pytz.timezone('Asia/Shanghai')  
 
 
def load_config(config_file): 
    """加载有效频道ID""" 
    tvg_ids = {} 
    try: 
        with open(config_file, 'r') as file: 
            tvg_ids = {line.strip():  line.strip()  for line in file if line.strip()}  
        logging.info(f"  已加载 {len(tvg_ids)} 个频道ID从 {config_file}") 
    except Exception as e: 
        logging.error(f"  读取配置文件失败 {config_file}: {e}") 
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
        logging.info(f"  已加载 {len(mapping)} 个频道映射从 {epg_match_file}") 
    except Exception as e: 
        logging.error(f"  加载映射文件失败 {epg_match_file}: {e}") 
    return mapping 
 
 
def normalize_channel_name(name, mapping, tvg_ids): 
    original_name = name 
    norm_id = mapping.get(name,  name) 
    if norm_id not in tvg_ids: 
        logging.debug(f"  频道未匹配: 原名 '{original_name}', 映射后 '{norm_id}' 不在配置ID中") 
    return norm_id if norm_id in tvg_ids else original_name 
 
 
def fetch_and_extract_xml(url): 
    try: 
        logging.info(f"Fetching   data from {url}") 
        response = requests.get(url,  timeout=10) 
        response.raise_for_status()   # 触发HTTP错误 
 
        # 检查内容类型是否为gzip或XML 
        content_type = response.headers.get('Content-Type',  '') 
        if 'gzip' in content_type or url.endswith('.gz'):  
            content = gzip.decompress(response.content)  
        else: 
            content = response.content  
 
        # 尝试解析XML 
        return ET.fromstring(content)  
    except requests.exceptions.HTTPError  as e: 
        logging.error(f"HTTP   错误 {e.response.status_code}   来自 {url}") 
    except Exception as e: 
        logging.error(f"  处理 {url} 失败: {str(e)}") 
    return None 
 
 
def parse_epg_time(start_time): 
    """解析EPG时间并转换为中国时区""" 
    if not start_time: 
        return None 
    try: 
        if len(start_time) == 14: 
            dt = datetime.datetime.strptime(start_time,  "%Y%m%d%H%M%S").replace(tzinfo=pytz.utc)  
        else: 
            # 提取基础时间部分 
            dt_part = start_time[:14] 
            dt = datetime.datetime.strptime(dt_part,  "%Y%m%d%H%M%S") 
 
            # 处理时区偏移 
            tz_part = start_time[14:] 
            if tz_part: 
                if tz_part[0] in '+-': 
                    sign = -1 if tz_part[0] == '-' else 1 
                    tz_str = tz_part[1:].ljust(4, '0') 
                    hours = int(tz_str[:2]) 
                    minutes = int(tz_str[2:4]) 
                    dt += sign * datetime.timedelta(hours=hours,  minutes=minutes) 
                elif tz_part.upper()  == 'Z': 
                    dt = dt.replace(tzinfo=datetime.timezone.utc)  
        # 转换为中国时区 
        dt = dt.astimezone(TIMEZONE)  
        logging.debug(f"Parsed  time: {dt}") 
        return dt 
    except Exception as e: 
        logging.error(f" 时间解析失败 '{start_time}': {e}") 
        return None 
 
 
def filter_and_build_epg(urls, mapping, tvg_ids): 
    valid_ids = set(tvg_ids.keys())  
    root_today = ET.Element('tv') 
    root_four_days = ET.Element('tv') 
    processed_channels = set() 
 
    now = datetime.datetime.now(TIMEZONE)  
    today_start = now.replace(hour=0,  minute=0, second=0, microsecond=0) 
    four_days_end = today_start + datetime.timedelta(days=4)  
 
    for url in urls: 
        epg_data = fetch_and_extract_xml(url) 
        if epg_data is None: 
            logging.warning(f"  跳过无效数据源: {url}") 
            continue 
 
        # 处理频道 
        channel_count = 0 
        for channel in epg_data.findall('channel'):  
            tvg_id = channel.get('id')  
            if not tvg_id: 
                continue 
            norm_id = normalize_channel_name(tvg_id, mapping, tvg_ids) 
            if norm_id in valid_ids and norm_id not in processed_channels: 
                # 更新频道信息 
                for elem in list(channel): 
                    if elem.tag  == 'display-name': 
                        channel.remove(elem)  
                ET.SubElement(channel, 'display-name', {'lang': 'zh'}).text = norm_id 
                channel.set('id',  norm_id) 
 
                # 添加到两个XML树 
                for root in [root_today, root_four_days]: 
                    root.append(deepcopy(channel))  
                processed_channels.add(norm_id)  
                channel_count += 1 
        logging.info(f"  从 {url} 处理 {channel_count} 个频道") 
 
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
 
            # 过滤掉早于今日开始时间的节目 
            if start_time < today_start: 
                continue 
 
            # 克隆并调整节目 
            prog = deepcopy(program) 
            prog.set('channel',  norm_id) 
 
            # 添加到今日EPG 
            if start_time < today_start + datetime.timedelta(days=1):  
                root_today.append(prog)  
            # 添加到四日EPG 
            if start_time < four_days_end: 
                root_four_days.append(prog)  
            program_count += 1 
        logging.info(f"  从 {url} 添加 {program_count} 个节目到四日EPG") 
 
    try: 
        # 确保 root_today 只包含当天的节目 
        for program in root_today.findall('programme'):  
            start_time = parse_epg_time(program.get('start'))  
            if start_time >= today_start + datetime.timedelta(days=1):  
                root_today.remove(program)  
 
        ET.ElementTree(root_today).write(output_file, encoding='utf-8', xml_declaration=True) 
        logging.info(f" 今日EPG已保存至 {output_file}") 
 
        if save_as_gz: 
            # 确保 root_four_days 只包含四天的节目 
            for program in root_four_days.findall('programme'):  
                start_time = parse_epg_time(program.get('start'))  
                if start_time >= four_days_end: 
                    root_four_days.remove(program)  
 
            with gzip.open(output_file_gz,  'wb') as f: 
                ET.ElementTree(root_four_days).write(f, encoding='utf-8', xml_declaration=True) 
            logging.info(f" 四日EPG已压缩保存至 {output_file_gz}") 
    except Exception as e: 
        logging.error(f" 保存文件失败") 

 
urls = [ 
    'https://raw.githubusercontent.com/sparkssssssssss/epg/main/pp.xml.gz',  
    'https://raw.githubusercontent.com/lxxcp/live/main/guide.xml',  
    'https://epg.pw/xmltv/epg_CN.xml',  
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
