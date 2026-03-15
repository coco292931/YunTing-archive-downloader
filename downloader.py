import requests
import os
from datetime import datetime, timedelta
import time
import hashlib
from urllib.parse import urlparse

def get_sign_and_timestamp(params, api_key="f0fc4c668392f9f9a447e48584c214ee", broadcast_id=None):
    """
    根据云听前端JS逻辑生成正确的 sign 和 timestamp
    """
    # 云听接口使用毫秒级时间戳参与签名，客户端和服务端必须保持同一轮计算口径。
    timestamp = str(int(time.time() * 1000))
    # 使用传入的 key 或者默认的硬编码 key
    key = api_key
    
    if isinstance(params, dict):
        # 按 key 排序后拼接，保证签名输入稳定（与前端 JS 实现一致）。
        sorted_keys = sorted(params.keys())
        sort_params = [f"{k}={params[k]}" for k in sorted_keys]
        params_str = "&".join(sort_params)
    else:
        # Fallback if params is the date string
        params_str = f"broadcastId={broadcast_id}&date={params}"
        
    sign_text = f"{params_str}&timestamp={timestamp}&key={key}"
    sign = hashlib.md5(sign_text.encode('utf-8')).hexdigest().upper()
    
    return sign, timestamp

def _load_downloaded_images(log_file):
    # 图片去重缓存：存储已下载 URL，避免重复请求相同图片地址。
    if not os.path.exists(log_file):
        return set()
    with open(log_file, 'r', encoding='utf-8') as f:
        return set(line.strip() for line in f if line.strip())

def _save_downloaded_image(log_file, url):
    # 追加写入，保持历史记录，便于跨天任务复用缓存。
    with open(log_file, 'a', encoding='utf-8') as f:
        f.write(f"{url}\n")

def download_image(url, img_dir, headers, downloaded_images_log, images_info_log, safe_program_name, suffix=""):
    # 返回值会写入节目清单文本，作为“图片处理结果”提示。
    if not url:
        return ""
    
    images_cache = _load_downloaded_images(downloaded_images_log)
        
    try:
        parsed_url = urlparse(url)
        # 用图片URL的最后一段作为文件名，如果有特殊字符这里暂且忽略，通常是随机字符串.jpg
        original_name = os.path.basename(parsed_url.path)
        if not original_name:
            original_name = hashlib.md5(url.encode('utf-8')).hexdigest() + ".jpg"

        _, ext = os.path.splitext(original_name)
        if not ext:
            ext = ".jpg"

        # 使用节目名称命名
        new_img_name = f"{safe_program_name}{suffix}{ext}"
        img_path = os.path.join(img_dir, new_img_name)
        
        # 双重去重：URL 命中缓存或目标文件已存在，都视为可跳过。
        is_cached = url in images_cache
        if os.path.exists(img_path) or is_cached:
            if not is_cached:
                _save_downloaded_image(downloaded_images_log, url)
            return f"（跳过：{new_img_name}）"
            
        print(f"正在下载图片: {url} -> {img_path}")
        img_response = requests.get(url, headers={'User-Agent': headers.get('user-agent', '')}, stream=True)
        img_response.raise_for_status()
        with open(img_path, 'wb') as f:
            for chunk in img_response.iter_content(chunk_size=8192):
                f.write(chunk)
                
        # 记录到已下载列表
        _save_downloaded_image(downloaded_images_log, url)

        # 写入图片详情txt
        with open(images_info_log, 'a', encoding='utf-8') as info_f:
            info_f.write(f"本地命名: {new_img_name}\n")
            info_f.write(f"原始文件: {original_name}\n")
            info_f.write(f"来源地址: {url}\n")
            info_f.write("-" * 40 + "\n")

        return f"（新保存：{new_img_name}）"
    except Exception as e:
        print(f"下载图片失败 {url}: {e}")
        return "（下载失败）"

def download_by_date(date_str, broadcast_id="662", base_downloads_dir="downloads", high_bitrate=True, download_imgs=True, api_key="f0fc4c668392f9f9a447e48584c214ee", state_checker=None, post_process_cb=None, download_progress_cb=None):
    """
    根据指定日期下载电台回放.
    日期格式应为 "YY-MM-DD", 例如 "25-12-22".
        回调约定:
            - state_checker(is_chunk=bool): GUI 用于暂停/停止协作式中断
            - post_process_cb(name, file_path, date): 单文件下载完成后触发后处理
            - download_progress_cb(byte_count): 用于实时速率统计
    """
    try:
        # 将 "YY-MM-DD" 格式转换为 "YYYY-MM-DD"
        input_date = datetime.strptime(date_str, "%y-%m-%d")
        formatted_date = input_date.strftime("%Y-%m-%d")
    except ValueError:
        print(f"错误：日期格式不正确: {date_str}。请使用 'YY-MM-DD' 格式。")
        return

    # Hit FM 的 channel_name 是 662
    # broadcast_id = "662"
    
    # 定义API参数
    api_params = {
        "date": formatted_date,
        "broadcastId": broadcast_id
    }
    
    # 构建URL
    api_url = f"https://ytmsout.radio.cn/web/appProgram/listByDate?date={formatted_date}&broadcastId={broadcast_id}"

    # 生成签名和时间戳
    sign, timestamp = get_sign_and_timestamp(api_params, api_key, broadcast_id)

    # 该请求头集合来自网页端行为，包含平台标识和签名字段。
    headers = {
        'accept': '*/*',
        'accept-language': 'zh,zh-CN;q=0.9,zh-TW;q=0.8',
        'content-type': 'application/json',
        'dnt': '1',
        'equipmentid': '0000',
        'origin': 'https://www.radio.cn',
        'platformcode': 'WEB',
        'referer': 'https://www.radio.cn/',
        'sec-ch-ua': '"Not:A-Brand";v="99", "Microsoft Edge";v="145", "Chromium";v="145"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'sec-gpc': '1',
        'sign': sign,
        'timestamp': timestamp,
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36 Edg/145.0.0.0',
    }

    print(f"正在获取 {formatted_date} 的节目列表...")
    print(f"使用 Timestamp: {timestamp}, Sign: {sign}")

    try:
        response = requests.get(api_url, headers=headers)
        response.raise_for_status()  # 如果请求失败则抛出异常
        program_data = response.json()
    except requests.exceptions.RequestException as e:
        print(f"错误：请求节目列表失败: {e}")
        return
    except ValueError: # JSONDecodeError
        print("错误：解析返回的 JSON 数据失败。")
        return

    if program_data.get("code") != 0 or not program_data.get("data"):
        print(f"在 {formatted_date} 未找到节目。服务器返回: {program_data.get('message', '无消息')}")
        return

    # 输出结构:
    # - downloads/YYYY-MM-DD/*.m4a
    # - downloads/images/*
    # - downloads/downloaded_images.txt
    output_dir = os.path.join(base_downloads_dir, formatted_date)
    images_dir = os.path.join(base_downloads_dir, "images")
    downloaded_images_log = os.path.join(base_downloads_dir, "downloaded_images.txt")
    images_info_log = os.path.join(images_dir, "images_info.txt")

    for path_to_create in [base_downloads_dir, output_dir, images_dir]:
        if not os.path.exists(path_to_create):
            os.makedirs(path_to_create)
    
    print(f"节目列表获取成功，准备下载...")

    # 保存每日节目信息的txt文件
    info_txt_path = os.path.join(output_dir, f"{formatted_date}_program_info.txt")
    with open(info_txt_path, 'w', encoding='utf-8') as info_file:
        info_file.write(f"=== {formatted_date} 节目信息 ===\n\n")

        for program in program_data["data"]:
            # 在“节目粒度”进行中断检查: 软停止会阻止后续节目继续下载。
            if state_checker:
                state_checker(is_chunk=False)
                
            program_name = program.get("programName", "unknown_program")
            start_time_ms = program.get("startTime", 0)
            end_time_ms = program.get("endTime", 0)
            
            # 格式化时间
            start_time_str = datetime.fromtimestamp(start_time_ms/1000.0).strftime('%Y-%m-%d %H:%M:%S') if start_time_ms else "未知"
            end_time_str = datetime.fromtimestamp(end_time_ms/1000.0).strftime('%Y-%m-%d %H:%M:%S') if end_time_ms else "未知"
            
            # 获取图片链接
            image_url = program.get("image", "")
            image_long_url = program.get("imageLong", "")
            
            # 文件名中可能包含非法字符，需要替换
            safe_program_name = "".join(c for c in program_name if c.isalnum() or c in (' ', '_')).rstrip()
            
            # 图片下载逻辑与音频下载解耦，失败不会阻断后续音频抓取。
            if download_imgs:
                img_result = download_image(image_url, images_dir, headers, downloaded_images_log, images_info_log, safe_program_name) if image_url else "无"
                img_long_result = download_image(image_long_url, images_dir, headers, downloaded_images_log, images_info_log, safe_program_name, "_long") if image_long_url else "无"
            else:
                img_result = "跳过"
                img_long_result = "跳过"

            # 决定使用哪种码率
            if high_bitrate:
                download_url = program.get("playUrlHigh")
                quality_str = "高码率"
            else:
                # 尝试获取低码率，找不到就用默认
                download_url = program.get("playUrlLow") or program.get("downloadUrl")
                quality_str = "低码率"

            # 将信息写入文本文件
            info_file.write(f"节目名称: {program_name}\n")
            info_file.write(f"音质: {quality_str}\n")
            info_file.write(f"开始时间: {start_time_str}\n")
            info_file.write(f"结束时间: {end_time_str}\n")
            info_file.write(f"下载链接: {download_url}\n")
            info_file.write(f"展示图片: {image_url} {img_result}\n")
            info_file.write(f"长版图片: {image_long_url} {img_long_result}\n")
            info_file.write("-" * 40 + "\n")

            if not download_url:
                print(f"警告：节目 '{program_name}' 没有找到{quality_str}下载链接，跳过。")
                continue

            file_name = f"{safe_program_name}.m4a"
            file_path = os.path.join(output_dir, file_name)
            part_path = file_path + ".part"

            if os.path.exists(file_path):
                print(f"文件 '{file_path}' 已存在，跳过下载。")
                # 即使是已存在文件，也触发后处理回调，便于 GUI 做统一转换排队。
                if post_process_cb:
                    post_process_cb(safe_program_name, file_path, formatted_date)
                continue

            print(f"正在下载 '{program_name}' 到 '{file_path}'...")

            try:
                # 下载文件时也带上部分请求头，尤其是 User-Agent 和 Referer
                download_headers = {
                    'User-Agent': headers['user-agent'],
                    'Referer': headers['referer']
                }
                audio_response = requests.get(download_url, headers=download_headers, stream=True)
                audio_response.raise_for_status()
                
                # 采用 .part 临时文件，确保中断时不会留下“看似完整”的坏文件。
                with open(part_path, 'wb') as f:
                    for chunk in audio_response.iter_content(chunk_size=8192):
                        if state_checker:
                            # 分块检查允许“强停”即时生效，同时“软停”在当前文件内继续写完。
                            state_checker(is_chunk=True)
                        if chunk:
                            if download_progress_cb:
                                try:
                                    # 统计回调不应影响主流程，异常直接吞掉。
                                    download_progress_cb(len(chunk))
                                except Exception:
                                    pass
                            f.write(chunk)
                
                # 下载完成后重命名，避免不完整文件干扰
                os.replace(part_path, file_path)
                print(f"'{program_name}' 下载完成。")

                if post_process_cb:
                    post_process_cb(safe_program_name, file_path, formatted_date)

            except Exception as e:
                # 无论发生什么异常，清理可能存在的 .part 文件
                if os.path.exists(part_path):
                    try:
                        os.remove(part_path)
                    except:
                        pass
                print(f"错误：下载 '{program_name}' 失败或被中断: {e}")
                # StopDownloadException 可能来自 GUI 模块，不同模块类身份不一致，
                # 这里按异常名识别并继续上抛，确保可中断整个日期循环。
                if type(e).__name__ == 'StopDownloadException':
                    raise

    print(f"\n{formatted_date} 的所有节目下载任务已完成。信息已保存至 {info_txt_path}\n")

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description="云听电台下载器")
    parser.add_argument("-d", "--date", help="指定单独日期 (如 '25-12-22') 或日期范围 (如 '25-11-22 to 25-12-22')", default="25-12-22")
    parser.add_argument("-b", "--broadcast", help="电台channel ID，默认是662 (Hit FM)", default="662")
    parser.add_argument("-o", "--outdir", help="基础输出目录，默认是'downloads'", default="downloads")
    parser.add_argument("--low-bitrate", help="下载低码率音频 (默认下载高码率)", action="store_true")
    parser.add_argument("--no-images", help="不下载封面图片", action="store_true")
    parser.add_argument("--api-key", help="接口签名鉴权用的固定密钥", default="f0fc4c668392f9f9a447e48584c214ee")
    parser.add_argument("--delay", help="多日持续下载时，每天之间的间隔时间(秒)", type=float, default=1.5)
    
    args = parser.parse_args()
    date_arg = args.date.strip()
    
    high_bit = not args.low_bitrate
    dl_imgs = not args.no_images
    
    # 命令行支持 "YY-MM-DD to YY-MM-DD" 范围写法。
    if " to " in date_arg:
        parts = date_arg.split(" to ")
        if len(parts) == 2:
            start_str, end_str = parts[0].strip(), parts[1].strip()
            try:
                start_date = datetime.strptime(start_str, "%y-%m-%d")
                end_date = datetime.strptime(end_str, "%y-%m-%d")
                
                if start_date > end_date:
                    print("错误：开始日期不能晚于结束日期。")
                else:
                    curr_date = start_date
                    while curr_date <= end_date:
                        download_by_date(
                            curr_date.strftime("%y-%m-%d"), 
                            broadcast_id=args.broadcast, 
                            base_downloads_dir=args.outdir, 
                            high_bitrate=high_bit, 
                            download_imgs=dl_imgs, 
                            api_key=args.api_key
                        )
                        curr_date += timedelta(days=1)
                        if curr_date <= end_date:
                            time.sleep(args.delay)
            except ValueError:
                print("错误：日期范围解析失败，请确保格式如 '25-11-22 to 25-12-22'。")
        else:
            print("错误：日期范围格式不正确。")
    else:
        # 单独日期下载
        download_by_date(
            date_arg, 
            broadcast_id=args.broadcast, 
            base_downloads_dir=args.outdir, 
            high_bitrate=high_bit, 
            download_imgs=dl_imgs, 
            api_key=args.api_key
        )

