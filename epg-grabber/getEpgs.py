import os
import gzip
import xml.etree.ElementTree as ET
import requests
import logging
from copy import deepcopy
import datetime
import pytz

# 配置参数
save_as_gz = True  # 是否保存 .gz 文件
config_file = os.path.join(os.path.dirname(__file__), 'config.txt')
epg_match_file = os.path.join(os.path.dirname(__file__), 'epg_match.xml')
output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'e.xml')
output_file_gz = output_file + '.gz'
TIMEZONE = pytz.timezone('Asia/Shanghai')  # 使用中国时区

def load_config(config_file):
    """加载 config.txt 文件中的有效频道ID"""
    tvg_ids = {}
    try:
        with open(config_file, 'r') as file:
            for line in file:
                line = line.strip()
                if line:
                    tvg_ids[line] = line
        logging.info(f"Loaded {len(tvg_ids)} TVG IDs from {config_file}")
    except Exception as e:
        logging.error(f"Failed to read {config_file}: {e}")
    return tvg_ids

def load_epg_mapping(epg_match_file):
    """加载频道名称映射表"""
    mapping = {}
    try:
        tree = ET.parse(epg_match_file)
        root = tree.getroot()
        for epg in root.findall('epg'):
            epgid = epg.find('epgid').text
            names = epg.find('name').text.split(',')
            for name in names:
                mapping[name.strip()] = epgid
        logging.info(f"Loaded {len(mapping)} channel mappings from {epg_match_file}")
    except Exception as e:
        logging.error(f"Failed to load {epg_match_file}: {e}")
    return mapping

def normalize_channel_name(name, mapping, tvg_ids):
    """标准化频道名称"""
    normalized_name = mapping.get(name, name)
    if normalized_name in tvg_ids:
        return normalized_name
    elif name in tvg_ids:
        return name
    else:
        return name

def fetch_and_extract_xml(url):
    """获取并解析XML数据"""
    try:
        logging.info(f"Fetching data from {url}")
        response = requests.get(url)
        response.raise_for_status()

        if url.endswith('.gz'):
            decompressed_data = gzip.decompress(response.content)
            return ET.fromstring(decompressed_data)
        else:
            return ET.fromstring(response.content)
    except requests.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
    except Exception as e:
        logging.error(f"Failed to process {url}: {e}")
    return None

def parse_epg_time(start_time):
    """解析EPG时间字符串（增加时区转换）"""
    if not start_time:
        return None
    try:
        time_part, tz_part = start_time.split()
        dt = datetime.datetime.strptime(time_part, "%Y%m%d%H%M%S")
        
        # 转换为带时区的datetime对象
        tz_sign = tz_part[0]
        tz_hours = int(tz_part[1:3])
        tz_mins = int(tz_part[3:5])
        tz_offset = datetime.timedelta(hours=tz_hours, minutes=tz_mins)
        if tz_sign == '-':
            tz_offset = -tz_offset
            
        dt = dt.replace(tzinfo=datetime.timezone(tz_offset))
        return dt.astimezone(TIMEZONE)  # 统一转换为中国时区
    except Exception as e:
        logging.error(f"Failed to parse time {start_time}: {e}")
        return None

def filter_and_build_epg(urls, mapping, tvg_ids):
    """主处理函数（关键修改）"""
    # 使用传入的tvg_ids字典的键作为有效ID集合
    valid_tvg_ids = set(tvg_ids.keys())
    logging.info(f"Using {len(valid_tvg_ids)} valid TVG IDs from config")

    # 创建XML根节点
    root_today = ET.Element('tv')  # 当天节目单
    root_four_days = ET.Element('tv')  # 四天节目单
    seen_channels = set()
    
    # 时间范围计算（基于中国时区）
    now = datetime.datetime.now(TIMEZONE)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + datetime.timedelta(days=1)
    four_days_end = today_start + datetime.timedelta(days=4)

    for url in urls:
        epg_data = fetch_and_extract_xml(url)
        if not epg_data:
            continue

        # 处理频道信息
        channel_count = 0
        for channel in epg_data.findall('channel'):
            tvg_id = channel.get('id')
            norm_id = normalize_channel_name(tvg_id, mapping, tvg_ids)
            
            if norm_id in valid_tvg_ids and norm_id not in seen_channels:
                # 清理并更新显示名称
                for elem in channel.findall('display-name'):
                    channel.remove(elem)
                ET.SubElement(channel, 'display-name', {'lang': 'zh'}).text = norm_id
                channel.set('id', norm_id)
                
                # 添加到两个XML树
                root_today.append(deepcopy(channel))
                root_four_days.append(deepcopy(channel))
                
                seen_channels.add(norm_id)
                channel_count += 1
        logging.info(f"Processed {channel_count} channels from {url}")

        # 处理节目信息
        for programme in epg_data.findall('programme'):
            tvg_id = programme.get('channel')
            norm_id = normalize_channel_name(tvg_id, mapping, tvg_ids)
            
            if norm_id not in valid_tvg_ids:
                continue

            # 时间解析（已转换为中国时区）
            start_time = parse_epg_time(programme.get('start'))
            if not start_time:
                continue

            # 克隆节目节点
            prog = deepcopy(programme)
            prog.set('channel', norm_id)

            # 判断是否在当天范围内
            if today_start <= start_time < today_end:
                root_today.append(prog)

            # 判断是否在四天范围内
            if today_start <= start_time < four_days_end:
                root_four_days.append(prog)

        logging.info(f"Processed programs from {url}")

    # 保存文件
    try:
        # 保存当天节目单为 e.xml
        with open(output_file, 'wb') as f:
            ET.ElementTree(root_today).write(f, encoding='utf-8', xml_declaration=True)
        logging.info(f"Today's EPG saved to {output_file}")

        # 保存四天节目单为 e.xml.gz
        if save_as_gz:
            with gzip.open(output_file_gz, 'wb') as f:
                ET.ElementTree(root_four_days).write(f, encoding='utf-8', xml_declaration=True)
            logging.info(f"Four-day EPG saved to {output_file_gz}")
    except Exception as e:
        logging.error(f"Failed to save files: {e}")

# EPG数据源列表
urls = [
    'https://raw.githubusercontent.com/sparkssssssssss/epg/main/pp.xml.gz',
    'https://github.com/lxxcp/live/blob/main/guide.xml',
    'https://epg.pw/xmltv/epg_CN.xml',
    'https://epg.pw/xmltv/epg_hk.xml.gz',
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
    
    # 加载配置
    channel_mapping = load_epg_mapping(epg_match_file)
    tvg_id_list = load_config(config_file)
    
    # 执行处理
    filter_and_build_epg(urls, channel_mapping, tvg_id_list)
