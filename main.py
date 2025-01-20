import requests
import re
from pathlib import Path

# 读取配置文件中的直播源地址
def read_config(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            lines = file.readlines()
        return [line.strip() for line in lines if line.strip()]
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return []

# 读取直播源文件（.txt 或 .m3u）
def read_stream_file(file_path):
    try:
        with open(file_path, "r", encoding="utf-8") as file:
            content = file.read()
        return content
    except Exception as e:
        print(f"读取直播源文件失败: {e}")
        return ""

# 解析直播源文件内容
def parse_stream_content(content):
    streams = []
    lines = content.splitlines()
    name = ""
    for line in lines:
        line = line.strip()
        if line.startswith("#EXTINF:"):
            # 提取频道名称
            match = re.search(r'#EXTINF:-1,(.*)', line)
            if match:
                name = match.group(1).strip()
        elif line and not line.startswith("#"):
            # 提取直播源URL
            url = line.strip()
            if name and url:
                streams.append({"name": name, "url": url})
                name = ""  # 重置名称
    return streams

# 校验直播源是否有效（简单示例：检查HTTP状态码）
def validate_stream(url):
    try:
        response = requests.head(url, timeout=5)
        return response.status_code == 200
    except requests.RequestException:
        return False

# 排序直播源（按名称排序）
def sort_streams(sources):
    return sorted(sources, key=lambda x: x["name"])

# 生成live.txt文件
def generate_txt_file(sources, output_file):
    with open(output_file, "w", encoding="utf-8") as file:
        for source in sources:
            file.write(f"{source['name']}: {source['url']}\n")

# 生成live.m3u文件
def generate_m3u_file(sources, output_file):
    with open(output_file, "w", encoding="utf-8") as file:
        file.write("#EXTM3U\n")
        for source in sources:
            file.write(f"#EXTINF:-1,{source['name']}\n")
            file.write(f"{source['url']}\n")

# 主程序
def main():
    config_file = "config.txt"  # 配置文件路径
    output_txt = "live.txt"
    output_m3u = "live.m3u"

    print("读取配置文件...")
    stream_files = read_config(config_file)
    if not stream_files:
        print("未找到有效的直播源文件路径，退出程序。")
        return

    all_streams = []
    for file_path in stream_files:
        if not Path(file_path).exists():
            print(f"文件不存在: {file_path}")
            continue

        print(f"读取直播源文件: {file_path}")
        content = read_stream_file(file_path)
        streams = parse_stream_content(content)
        all_streams.extend(streams)

    print("校验直播源...")
    valid_streams = [stream for stream in all_streams if validate_stream(stream["url"])]
    print(f"校验完成，有效直播源数量: {len(valid_streams)}")

    print("排序直播源...")
    sorted_streams = sort_streams(valid_streams)

    print("生成live.txt文件...")
    generate_txt_file(sorted_streams, output_txt)

    print("生成live.m3u文件...")
    generate_m3u_file(sorted_streams, output_m3u)

    print("完成！")

if __name__ == "__main__":
    main()