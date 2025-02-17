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
        logging.info(f"Loaded  {len(tvg_ids)} TVG IDs from {config_file}")
    except Exception as e:
        logging.error(f"Failed  to read {config_file}: {e}")
    return tvg_ids 
 
def load_epg_mapping(epg_match_file):
    """加载频道名称映射表"""
    mapping = {}
    try:
        tree = ET.parse(epg_match_file) 
        for epg in tree.findall('epg'): 
            epgid = epg.find('epgid').text  
            names = epg.find('name').text.split(',') 
            mapping.update({name.strip():  epgid for name in names})
        logging.info(f"Loaded  {len(mapping)} channel mappings from {epg_match_file}")
    except Exception as e:
        logging.error(f"Failed  to load {epg_match_file}: {e}")
    return mapping 
 
def normalize_channel_name(name, mapping, tvg_ids):
    """标准化频道名称"""
    return mapping.get(name,  name) if mapping.get(name,  name) in tvg_ids else name 
 
def fetch_and_extract_xml(url):
    """获取并解析XML数据"""
    try:
        logging.info(f"Fetching  data from {url}")
        response = requests.get(url,  timeout=10)
        response.raise_for_status() 
        
        content = gzip.decompress(response.content)  if url.endswith('.gz')  else response.content  
        return ET.fromstring(content) 
    except Exception as e:
        logging.error(f"Failed  to process {url}: {e}")
    return None 
 
def parse_epg_time(start_time):
    """解析EPG时间并转换为中国时区（修复时间分割问题）"""
    if not start_time:
        return None 
 
    try:
        # 基础时间部分处理（至少14位：YYYYMMDDHHMMSS）
        if len(start_time) < 14:
            raise ValueError("时间字符串过短")
 
        dt_part = start_time[:14]
        dt = datetime.datetime.strptime(dt_part,  "%Y%m%d%H%M%S")
 
        # 时区处理（支持多种格式）
        tz_part = start_time[14:]
        offset = datetime.timedelta(0) 
 
        if tz_part:
            # 处理带符号的时区格式（±HHMM / ±HH）
            if tz_part[0] in '+-':
                sign = -1 if tz_part[0] == '-' else 1 
                tz_str = tz_part[1:].zfill(4)  # 统一为4位数字 
                hours = int(tz_str[:2])
                minutes = int(tz_str[2:4]) if len(tz_str) >=4 else 0 
                offset = sign * datetime.timedelta(hours=hours,  minutes=minutes)
            # 处理UTC标识（Z）
            elif tz_part[0].upper() == 'Z':
                offset = datetime.timedelta(0) 
        
        # 应用时区偏移 
        dt = dt.replace(tzinfo=datetime.timezone(offset)).astimezone(TIMEZONE) 
        return dt 
 
    except Exception as e:
        logging.error(f" 时间解析失败 {start_time}: {e}")
        return None 
 
def filter_and_build_epg(urls, mapping, tvg_ids):
    """主处理函数（已修复时间范围问题）"""
    valid_ids = set(tvg_ids.keys()) 
    logging.info(f" 使用 {len(valid_ids)} 个有效频道ID")
    
    # 初始化XML结构 
    root_today = ET.Element('tv')
    root_four_days = ET.Element('tv')
    processed_channels = set()
 
    # 时间范围计算（基于中国时区）
    now = datetime.datetime.now(TIMEZONE) 
    today_start = now.replace(hour=0,  minute=0, second=0, microsecond=0)
    four_days_end = today_start + datetime.timedelta(days=4) 
 
    for url in urls:
        if not (epg_data := fetch_and_extract_xml(url)): continue 
 
        # 处理频道信息 
        channel_count = 0 
        for channel in epg_data.findall('channel'): 
            if (tvg_id := channel.get('id'))  and (norm_id := normalize_channel_name(tvg_id, mapping, tvg_ids)) in valid_ids:
                if norm_id not in processed_channels:
                    # 清理并更新频道显示名称 
                    channel[:] = [e for e in channel if e.tag  != 'display-name']
                    ET.SubElement(channel, 'display-name', {'lang': 'zh'}).text = norm_id 
                    channel.set('id',  norm_id)
                    
                    # 深拷贝频道节点到两个XML树 
                    for root in [root_today, root_four_days]:
                        root.append(deepcopy(channel)) 
                    processed_channels.add(norm_id) 
                    channel_count += 1 
        logging.info(f" 从 {url} 处理 {channel_count} 个频道")
 
        # 处理节目信息 
        program_count = 0 
        for program in epg_data.findall('programme'): 
            if (tvg_id := program.get('channel'))  and (norm_id := normalize_channel_name(tvg_id, mapping, tvg_ids)) in valid_ids:
                if (start_time := parse_epg_time(program.get('start')))  and (start_time >= today_start):
                    # 克隆节目节点 
                    prog = deepcopy(program)
                    prog.set('channel',  norm_id)
                    
                    # 添加到对应XML树 
                    if start_time < (today_start + datetime.timedelta(days=1)): 
                        root_today.append(prog) 
                    if start_time < four_days_end:
                        root_four_days.append(prog) 
                        program_count += 1 
        logging.info(f" 从 {url} 添加 {program_count} 个节目")
 
    # 保存文件 
    try:
        ET.ElementTree(root_today).write(output_file, encoding='utf-8', xml_declaration=True)
        logging.info(f" 今日EPG已保存至 {output_file}")
        
        if save_as_gz:
            with gzip.open(output_file_gz,  'wb') as f:
                ET.ElementTree(root_four_days).write(f, encoding='utf-8', xml_declaration=True)
            logging.info(f" 四日EPG已压缩保存至 {output_file_gz}")
    except Exception as e:
        logging.error(f" 文件保存失败: {e}")


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
