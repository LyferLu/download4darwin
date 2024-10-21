import os
import asyncio
import re
from telethon import TelegramClient, events
from telethon.tl.types import DocumentAttributeVideo
from yt_dlp import YoutubeDL
import cv2  # 用于获取视频的宽度和高度信息

# 你的API ID和API Hash
API_ID = 'YOUR_API_ID'
API_HASH = 'YOUR_API_HASH'
BOT_TOKEN = 'YOUR_BOT_TOKEN'

# 创建一个TelegramClient对象
client = TelegramClient('bot', API_ID, API_HASH)

# 定义/start命令的处理函数
@client.on(events.NewMessage(pattern='/start'))
async def start(event):
    start_text = (
        "您好！我是download4darwin，一个用于为darwin提供视频编码兼容下载YouTube视频的Bot。\n"
        "您可以使用/help获取帮助信息\n"
    )
    await event.respond(start_text)

# 定义/help命令的处理函数
@client.on(events.NewMessage(pattern='/help'))
async def help_command(event):
    help_text = (
        "欢迎使用download4darwin\n\n"
        "你可以使用以下命令：\n"
        "/start - 启动Bot\n"
        "/help - 获取帮助信息\n"
        "/dl4dw <URL> - 下载YouTube视频\n"
    )
    await event.respond(help_text)

# 定义/dl4dw命令的处理函数，用于下载YouTube视频
@client.on(events.NewMessage(pattern='/dl4dw'))
async def dl4dw(event):
    args = event.message.message.split()
    if len(args) < 2:
        await event.respond('请提供一个YouTube视频链接，例如：/dl4dw <URL>')
        return
    
    # 使用正则表达式过滤URL前后的多余文本
    url_pattern = re.compile(r'(https?://[^\s]+)')
    match = url_pattern.search(event.message.message)
    if not match:
        await event.respond('未找到有效的YouTube视频链接，请提供一个有效的URL。')
        return

    url = match.group(1)

    # 下载视频的配置
    ydl_opts = {
        # 'format': '(bv*[vcodec^=avc1]/bv*)+(ba[acodec^=mp4a]/ba)',  # 下载视频编码为avc1和音频编码为mp4a的视频
        # 'format': 'bv*[filesize<150M]+ba[filesize<50M]',  # 下载小于150MB的视频和小于50MB的音频
        'format': 'bv*[filesize<300M][vcodec^=avc1]+ba[filesize<50M][acodec^=mp4a]', # 下载视频编码为avc1且小于150MB的视频和音频编码为mp4a且小于50MB的音频
        # 'outtmpl': 'downloaded_video.%(ext)s',  # 保存文件的命名模板
        # 'noplaylist': True,  # 不下载播放列表
        # 'quiet': True,  # 安静模式
        # 'no_warnings': True,  # 不显示警告
        # 'max_filesize': 200 * 1024 * 1024,  # 限制下载文件大小为50MB
        'outtmpl': '%(title).200B%(title.201B&…|)s [%(id)s].%(ext)s',  # 输出限制为200字符
    }

    # 发送“正在下载视频，请稍候...”消息并保存消息ID
    downloading_message = await event.respond('正在下载视频，请稍候...')

    try:
        # 使用yt-dlp下载视频
        with YoutubeDL(ydl_opts) as ydl:
            info_dict = ydl.extract_info(url, download=True)
            video_filename = ydl.prepare_filename(info_dict)

        # 获取视频的宽度、高度和时长信息
        cap = cv2.VideoCapture(video_filename)
        if not cap.isOpened():
            raise Exception("无法打开视频文件")

        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        duration = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) / cap.get(cv2.CAP_PROP_FPS))
        
        # 截取视频的第二帧作为预览图
        cap.set(cv2.CAP_PROP_POS_FRAMES, 1)  # 设置到第二帧
        ret, frame = cap.read()
        if ret:
            preview_image_filename = os.path.splitext(video_filename)[0] + '.jpg'
            cv2.imwrite(preview_image_filename, frame)
        cap.release()

        # 创建视频属性
        attributes = [
            DocumentAttributeVideo(
                duration=duration,  # 您可以設置實際的視頻時長（以秒為單位）
                w=width,
                h=height,
                supports_streaming=True
            )
        ]

        # 发送视频文件和预览图像给用户
        await client.send_file(
            event.chat_id,
            video_filename,
            thumb=preview_image_filename,
            supports_streaming=True,
            attributes=attributes
        )
        
        # 删除视频文件和预览图像以节省空间
        os.remove(video_filename)
        os.remove(preview_image_filename)

        # 删除“正在下载视频，请稍候...”消息
        await client.delete_messages(event.chat_id, downloading_message)

    except Exception as e:
        await event.respond(f'下载视频时出错：{e}')
        # 删除视频文件和预览图像以节省空间
        if os.path.exists(video_filename):
            os.remove(video_filename)
        if os.path.exists(preview_image_filename):
            os.remove(preview_image_filename)
        # 删除“正在下载视频，请稍候...”消息
        await client.delete_messages(event.chat_id, downloading_message)

# 主函数
async def main():
    # 连接到Telegram服务器
    await client.start(bot_token=BOT_TOKEN)
    # 使Bot持续运行，直到按下Ctrl+C
    await client.run_until_disconnected()

if __name__ == '__main__':
    try:
        # 使用asyncio.run()来运行主函数
        asyncio.run(main())
    except KeyboardInterrupt:
        print("程序已被用户中断")