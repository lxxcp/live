import os
import gzip
import xml.etree.ElementTree as ET
import requests
import logging
from copy import deepcopy
import datetime
import pytz

# 配置参数
config_file = os.path.join(os.path.dirname(__file__), 'config.txt')
epg_match_file = os.path.join(os.path.dirname(__file__), 'epg_match.xml')
output_file_gz = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'e.xml.gz')
TIMEZONE = pytz.timezone('Asia/Shanghai')

def load_config(config_file):
    """加载有效频道ID"""
    tvg_ids = {}
    try:
        with open(config_file, 'r') as file:
            tvg_ids = {line.strip(): line.strip() for line in file if line.strip()}
        logging.info(f"   已加载 {len(tvg_ids)} 个频道ID从 {config_file}") 
    except Exception as e:
        logging.error(f"   读取配置文件失败 {config_file}: {e}")
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
        logging.info(f"   已加载 {len(mapping)} 个频道映射从 {epg_match_file}")
    except Exception as e:
        logging.error(f"   加载映射文件失败 {epg_match_file}: {e}")
    return mapping

def normalize_channel_name(name, mapping):
    """标准化频道名称（仅映射，不验证）"""
    return mapping.get(name, name)

def fetch_and_extract_xml(url):
    try:
        logging.info(f"   正在获取数据: {url}")
        response = requests.get(url, timeout=20)
        response.raise_for_status()

        # 处理压缩内容
        if response.headers.get('Content-Encoding') == 'gzip' or url.endswith('.gz'):
            content = gzip.decompress(response.content)
        else:
            content = response.content

        return ET.fromstring(content)
    except Exception as e:
        logging.error(f"   处理 {url} 失败: {str(e)}")
        return None

def parse_epg_time(start_time):
    """解析EPG时间并转换为中国时区"""
    if not start_time:
        return None
    try:
        clean_time = start_time.replace(" ", "")
        base_time = clean_time[:14]
        tz_marker = clean_time[14:] if len(clean_time) > 14 else ''

        dt = datetime.datetime.strptime(base_time, "%Y%m%d%H%M%S")

        if tz_marker.upper() == 'Z':
            dt = pytz.utc.localize(dt).astimezone(TIMEZONE)
        elif tz_marker:
            offset = datetime.datetime.strptime(tz_marker, "%z").utcoffset()
            dt = dt.replace(tzinfo=datetime.timezone(offset)).astimezone(TIMEZONE)
        else:
            dt = TIMEZONE.localize(dt)
        return dt
    except Exception as e:
        logging.error(f"时间解析失败 '{start_time}': {e}")
        return None

def format_epg_time(dt):
    """将 datetime 对象格式化为 EPG 时间字符串"""
    return dt.strftime("%Y%m%d%H%M%S +0800")

def is_programme_valid(start_time, today_start):
    """检查节目时间是否为今天及今天以后"""
    parsed_time = parse_epg_time(start_time)
    return parsed_time is not None and parsed_time >= today_start

def process_sources(urls, mapping, tvg_ids):
    valid_ids = set(tvg_ids.keys())
    channels_dict = {}
    programmes_dict = {}

    # 获取当天零点时间
    now = datetime.datetime.now(TIMEZONE)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)

    # 第一阶段：收集所有数据
    for url in urls:
        epg_data = fetch_and_extract_xml(url)
        if epg_data is None:
            continue

        # 统计原始数据量
        original_channels = len(epg_data.findall('channel'))
        original_programmes = len(epg_data.findall('programme'))
        processed_channels = 0
        processed_programmes = 0

        # 处理频道信息
        for channel in epg_data.findall('channel'):
            original_id = channel.get('id')
            if not original_id:
                continue
            norm_id = normalize_channel_name(original_id, mapping)
            if norm_id in valid_ids and norm_id not in channels_dict:
                new_channel = deepcopy(channel)
                for elem in new_channel.findall('display-name'):
                    new_channel.remove(elem)
                ET.SubElement(new_channel, 'display-name', {'lang': 'zh'}).text = norm_id
                new_channel.set('id', norm_id)
                channels_dict[norm_id] = new_channel
                processed_channels += 1

        # 处理节目信息
        for programme in epg_data.findall('programme'):
            original_id = programme.get('channel')
            if not original_id:
                continue
            norm_id = normalize_channel_name(original_id, mapping)
            if norm_id not in valid_ids:
                continue

            start_time = programme.get('start')
            stop_time = programme.get('stop')
            parsed_start_time = parse_epg_time(start_time)
            parsed_stop_time = parse_epg_time(stop_time)

            if parsed_start_time is None or parsed_stop_time is None:
                continue

            if not is_programme_valid(start_time, today_start):
                continue

            new_start_time = format_epg_time(parsed_start_time)
            new_stop_time = format_epg_time(parsed_stop_time)
            programme.set('start', new_start_time)
            programme.set('stop', new_stop_time)

            if norm_id not in programmes_dict:
                programmes_dict[norm_id] = []
            programmes_dict[norm_id].append(programme)
            processed_programmes += 1

        logging.info(f"   已处理 {url}")
        logging.info(f"   └── 原始频道: {original_channels} → 有效频道: {processed_channels}")
        logging.info(f"   └── 原始节目: {original_programmes} → 有效节目: {processed_programmes}\n")

    # 第二阶段：节目去重
    logging.info(" 开始节目去重处理...")
    for channel_id in programmes_dict:
        seen = set()
        unique_programmes = []
        for prog in programmes_dict[channel_id]:
            title_elem = prog.find('title')
            title = title_elem.text if title_elem is not None else ''
            desc_elem = prog.find('desc')
            desc = desc_elem.text if desc_elem is not None else ''
            key = f"{prog.get('start')}|{title}|{desc}"
            if key not in seen:
                seen.add(key)
                unique_programmes.append(prog)
        programmes_dict[channel_id] = unique_programmes
        logging.info(f"   频道 {channel_id} 去重后保留 {len(unique_programmes)} 个节目")

    # 第三阶段：构建最终XML
    root = ET.Element('tv')
    
    # 添加频道信息
    for channel in channels_dict.values():
        root.append(deepcopy(channel))
    
    # 添加节目信息
    total_programs = 0
    for channel_id, progs in programmes_dict.items():
        for prog in progs:
            new_prog = deepcopy(prog)
            new_prog.set('channel', channel_id)
            root.append(new_prog)
            total_programs += 1
    
    logging.info(f" 最终包含 {len(channels_dict)} 个频道和 {total_programs} 个节目")

    # 保存文件
    xml_string = ET.tostring(root, encoding='utf-8', method='xml')
    xml_header = b'<?xml version="1.0" encoding="utf-8"?>'
    xml_with_header = xml_header + xml_string
    
    try:
        with gzip.open(output_file_gz, 'wb') as f:
            f.write(xml_with_header)
        logging.info(f"EPG 文件已压缩保存至 {output_file_gz}")
    except Exception as e:
        logging.error(f"   文件保存失败: {e}")

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
    process_sources(urls, channel_mapping, tvg_id_list)