import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import gzip
from datetime import datetime, timedelta
import logging

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# 电视猫的节目单页面URL
BASE_URL = "https://www.tvmao.com/program"

# 获取所有频道的链接
def get_channel_links():
    try:
        response = requests.get(BASE_URL, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        channels = soup.find_all('a', class_='channel')
        return [channel['href'] for channel in channels]
    except requests.RequestException as e:
        logging.error(f"获取频道链接失败: {e}")
        return []

# 获取某个频道的节目单
def get_program_list(channel_url):
    try:
        response = requests.get(channel_url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'lxml')
        programs = soup.find_all('div', class_='program')
        program_list = []
        for program in programs:
            time = program.find('span', class_='time').text.strip()
            name = program.find('span', class_='name').text.strip()
            program_list.append((time, name))
        return program_list
    except requests.RequestException as e:
        logging.error(f"获取节目单失败: {e}")
        return []

# 生成一天的节目单
def generate_daily_xml(channel_links, date):
    root = ET.Element("tv")
    for link in channel_links:
        channel_name = link.split('/')[-1]
        channel_element = ET.SubElement(root, "channel", id=channel_name)
        program_list = get_program_list(link)
        for time, name in program_list:
            program_element = ET.SubElement(channel_element, "program")
            ET.SubElement(program_element, "time").text = time
            ET.SubElement(program_element, "name").text = name
    tree = ET.ElementTree(root)
    tree.write(f"E_{date}.xml", encoding='utf-8', xml_declaration=True)
    logging.info(f"生成一天的节目单: E_{date}.xml")

# 生成七天的节目单并压缩
def generate_weekly_xml(channel_links):
    root = ET.Element("tv")
    for i in range(7):
        date = (datetime.now() + timedelta(days=i)).strftime('%Y-%m-%d')
        for link in channel_links:
            channel_name = link.split('/')[-1]
            channel_element = ET.SubElement(root, "channel", id=f"{channel_name}_{date}")
            program_list = get_program_list(link)
            for time, name in program_list:
                program_element = ET.SubElement(channel_element, "program")
                ET.SubElement(program_element, "time").text = time
                ET.SubElement(program_element, "name").text = name
    tree = ET.ElementTree(root)
    with gzip.open('e.xml.gz', 'wb') as f:
        f.write(ET.tostring(tree.getroot(), encoding='utf-8', method='xml'))
    logging.info("生成七天的节目单: e.xml.gz")

# 主函数
def main():
    channel_links = get_channel_links()
    if not channel_links:
        logging.error("未获取到频道链接，程序退出")
        return
    today = datetime.now().strftime('%Y-%m-%d')
    generate_daily_xml(channel_links, today)
    generate_weekly_xml(channel_links)

if __name__ == "__main__":
    main()
