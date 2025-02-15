import requests
from bs4 import BeautifulSoup
import xml.etree.ElementTree as ET
import gzip
from datetime import datetime, timedelta

# 电视猫的节目单页面URL
BASE_URL = "https://www.tvmao.com/program"

# 获取所有频道的链接
def get_channel_links():
    response = requests.get(BASE_URL)
    soup = BeautifulSoup(response.text, 'lxml')
    channels = soup.find_all('a', class_='channel')
    return [channel['href'] for channel in channels]

# 获取某个频道的节目单
def get_program_list(channel_url):
    response = requests.get(channel_url)
    soup = BeautifulSoup(response.text, 'lxml')
    programs = soup.find_all('div', class_='program')
    program_list = []
    for program in programs:
        time = program.find('span', class_='time').text
        name = program.find('span', class_='name').text
        program_list.append((time, name))
    return program_list

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

# 主函数
def main():
    channel_links = get_channel_links()
    today = datetime.now().strftime('%Y-%m-%d')
    generate_daily_xml(channel_links, today)
    generate_weekly_xml(channel_links)

if __name__ == "__main__":
    main()