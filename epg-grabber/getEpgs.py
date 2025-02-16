import os
import gzip
import xml.etree.ElementTree as ET
import requests
import logging
from copy import deepcopy
import datetime

save_as_gz = True  # 是否保存 .gz 文件
tvg_ids_file = os.path.join(os.path.dirname(__file__), 'tvg-ids.txt')
epg_match_file = os.path.join(os.path.dirname(__file__), 'epg_match.xml')
output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'e.xml')
output_file_gz = output_file + '.gz'

def load_tvg_ids(tvg_ids_file):
    # ...（保持不变）...

def load_epg_mapping(epg_match_file):
    # ...（保持不变）...

def normalize_channel_name(name, mapping, tvg_ids):
    # ...（保持不变）...

def fetch_and_extract_xml(url):
    # ...（保持不变）...

def parse_epg_time(start_time):
    """解析EPG时间字符串，返回UTC datetime对象"""
    if not start_time:
        return None
    try:
        parts = start_time.split(' ')
        if len(parts) != 2:
            return None
        time_part, tz_part = parts
        dt = datetime.datetime.strptime(time_part, "%Y%m%d%H%M%S")
        tz_sign = tz_part[0]
        tz_hours = int(tz_part[1:3])
        tz_mins = int(tz_part[3:5])
        tz_offset = datetime.timedelta(hours=tz_hours, minutes=tz_mins)
        if tz_sign == '-':
            tz_offset = -tz_offset
        utc_dt = dt - tz_offset
        utc_dt = utc_dt.replace(tzinfo=datetime.timezone.utc)
        return utc_dt
    except Exception as e:
        logging.error(f"解析时间失败 {start_time}: {e}")
        return None

def filter_and_build_epg(urls, mapping, tvg_ids):
    try:
        with open(tvg_ids_file, 'r') as file:
            valid_tvg_ids = set(line.strip() for line in file)
        logging.info(f"从 {tvg_ids_file} 加载了 {len(valid_tvg_ids)} 个有效TVG ID")
    except Exception as e:
        logging.error(f"读取 {tvg_ids_file} 失败: {e}")
        return

    # 创建两个根元素分别存储当日和四日数据
    root_daily = ET.Element('tv')
    root_four_days = ET.Element('tv')
    seen_channels = set()  # 记录已处理的频道
    today = datetime.datetime.utcnow().date()
    four_days_max = today + datetime.timedelta(days=3)

    for url in urls:
        epg_data = fetch_and_extract_xml(url)
        if epg_data is None:
            continue

        # 处理频道
        channel_count = 0
        for channel in epg_data.findall('channel'):
            tvg_id = channel.get('id')
            normalized_tvg_id = normalize_channel_name(tvg_id, mapping, tvg_ids)
            if normalized_tvg_id in valid_tvg_ids and normalized_tvg_id not in seen_channels:
                # 清理原有display-name
                for old_display in channel.findall('display-name'):
                    channel.remove(old_display)
                # 添加新display-name
                display_name = ET.SubElement(channel, 'display-name')
                display_name.set('lang', 'zh')
                display_name.text = normalized_tvg_id
                channel.set('id', normalized_tvg_id)
                
                # 深拷贝并添加到两个根元素
                channel_daily = deepcopy(channel)
                channel_four = deepcopy(channel)
                root_daily.append(channel_daily)
                root_four_days.append(channel_four)
                seen_channels.add(normalized_tvg_id)
                channel_count += 1
        logging.info(f"从 {url} 获取了 {channel_count} 个频道")

        # 处理节目
        prog_daily_count = 0
        prog_four_count = 0
        for programme in epg_data.findall('programme'):
            tvg_id = programme.get('channel')
            normalized_tvg_id = normalize_channel_name(tvg_id, mapping, tvg_ids)
            if normalized_tvg_id not in valid_tvg_ids:
                continue

            # 解析时间
            start_time = programme.get('start')
            utc_dt = parse_epg_time(start_time)
            if not utc_dt:
                continue
            prog_date = utc_dt.date()

            # 深拷贝节目并设置频道ID
            prog_copy = deepcopy(programme)
            prog_copy.set('channel', normalized_tvg_id)

            # 添加到当日数据
            if prog_date == today:
                root_daily.append(prog_copy)
                prog_daily_count += 1
            
            # 添加到四日数据
            if prog_date <= four_days_max:
                # 需要再次深拷贝，因为元素不能有多个父节点
                prog_copy_four = deepcopy(prog_copy)
                root_four_days.append(prog_copy_four)
                prog_four_count += 1

        logging.info(f"从 {url} 处理了 {prog_daily_count} 当日节目和 {prog_four_count} 四日节目")

    # 保存文件
    try:
        # 保存当日EPG
        ET.ElementTree(root_daily).write(output_file, encoding='utf-8', xml_declaration=True)
        logging.info(f"当日EPG已保存至 {output_file}")

        # 保存四日EPG（压缩）
        if save_as_gz:
            with gzip.open(output_file_gz, 'wb') as f:
                ET.ElementTree(root_four_days).write(f, encoding='utf-8', xml_declaration=True)
            logging.info(f"四日EPG已压缩保存至 {output_file_gz}")
    except Exception as e:
        logging.error(f"保存文件失败: {e}")

urls = [
    # ...（URL列表保持不变）...
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    mapping = load_epg_mapping(epg_match_file)
    tvg_ids = load_tvg_ids(tvg_ids_file)
    filter_and_build_epg(urls, mapping, tvg_ids)