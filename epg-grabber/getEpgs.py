import os
import gzip
import xml.etree.ElementTree as ET
import requests
import logging

save_as_gz = True  # 是否保存 .gz 文件
tvg_ids_file = os.path.join(os.path.dirname(__file__), 'tvg-ids.txt')
epg_match_file = os.path.join(os.path.dirname(__file__), 'epg_match.xml')
output_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'e.xml')
output_file_gz = output_file + '.gz'

def load_tvg_ids(tvg_ids_file):
    """
    加载 tvg-ids.txt 文件，构建频道 ID 到显示名称的映射表
    """
    tvg_ids = {}
    try:
        with open(tvg_ids_file, 'r') as file:
            for line in file:
                line = line.strip()
                if line:
                    tvg_ids[line] = line
        logging.info(f"Loaded {len(tvg_ids)} TVG IDs from {tvg_ids_file}")
    except Exception as e:
        logging.error(f"Failed to read {tvg_ids_file}: {e}")
    return tvg_ids

def load_epg_mapping(epg_match_file):
    """
    加载 epg_match.xml 文件，构建频道名称到标准名称的映射表
    """
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

def normalize_channel_name(name, mapping):
    """
    根据映射表将频道名称规范化
    """
    return mapping.get(name, name)

def fetch_and_extract_xml(url):
    """
    从 URL 获取 XML 数据并解析
    """
    try:
        logging.info(f"Fetching data from {url}")
        response = requests.get(url)
        response.raise_for_status()  # 检查请求是否成功

        if url.endswith('.gz'):
            try:
                decompressed_data = gzip.decompress(response.content)
                return ET.fromstring(decompressed_data)
            except Exception as e:
                logging.error(f"Failed to decompress and parse XML from {url}: {e}")
                return None
        else:
            try:
                return ET.fromstring(response.content)
            except Exception as e:
                logging.error(f"Failed to parse XML from {url}: {e}")
                return None
    except requests.RequestException as e:
        logging.error(f"Failed to fetch {url}: {e}")
        return None

def filter_and_build_epg(urls, mapping, tvg_ids):
    """
    过滤并构建 EPG 数据
    """
    try:
        with open(tvg_ids_file, 'r') as file:
            valid_tvg_ids = set(line.strip() for line in file)
        logging.info(f"Loaded {len(valid_tvg_ids)} valid TVG IDs from {tvg_ids_file}")
    except Exception as e:
        logging.error(f"Failed to read {tvg_ids_file}: {e}")
        return

    root = ET.Element('tv')

    for url in urls:
        epg_data = fetch_and_extract_xml(url)
        if epg_data is None:
            continue

        for channel in epg_data.findall('channel'):
            tvg_id = channel.get('id')
            normalized_tvg_id = normalize_channel_name(tvg_id, mapping)
            if normalized_tvg_id in valid_tvg_ids:
                # 删除原有 display-name 标签
                for old_display in channel.findall('display-name'):
                    channel.remove(old_display)
                
                # 创建新的 display-name
                display_name_elem = ET.SubElement(channel, 'display-name')
                display_name_elem.set('lang', 'zh')
                display_name_elem.text = normalized_tvg_id  # 直接使用标准化后的 ID 作为文本
                
                # 更新 channel 的 id
                channel.set('id', normalized_tvg_id)
                root.append(channel)

        for programme in epg_data.findall('programme'):
            tvg_id = programme.get('channel')
            normalized_tvg_id = normalize_channel_name(tvg_id, mapping)
            if normalized_tvg_id in valid_tvg_ids:
                programme.set('channel', normalized_tvg_id)
                root.append(programme)

    # 后续保存代码保持不变...
    try:
        tree = ET.ElementTree(root)
        tree.write(output_file, encoding='utf-8', xml_declaration=True)
        logging.info(f"New EPG saved to {output_file}")

        if save_as_gz:
            with gzip.open(output_file_gz, 'wb') as f:
                tree.write(f, encoding='utf-8', xml_declaration=True)
            logging.info(f"New EPG saved to {output_file_gz}")
    except Exception as e:
        logging.error(f"Failed to save EPG file: {e}")

urls = [
    'https://gitee.com/taksssss/tv/raw/main/epg/112114.xml.gz', 
    'https://gitee.com/taksssss/tv/raw/main/epg/51zmt.xml.gz',
    'https://gitee.com/taksssss/tv/raw/main/epg/livednow.xml.gz',
    'https://gitee.com/taksssss/tv/raw/main/epg/epgpw_cn.xml.gz',
    'https://e.erw.cc/all.xml.gz',
]

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    
    # 加载频道名称映射表
    mapping = load_epg_mapping(epg_match_file)
    
    # 加载 tvg-ids.txt 文件中的频道 ID 和显示名称
    tvg_ids = load_tvg_ids(tvg_ids_file)
    
    # 过滤并构建 EPG 数据
    filter_and_build_epg(urls, mapping, tvg_ids)