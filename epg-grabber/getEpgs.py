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