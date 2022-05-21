import asyncio
import os
import time
from queue import Queue
from urllib import parse

from requests import Session

from .routers.user import User
from .common import CourseHelperException
from .routers.websocket import ConnectionManager


class Downloader:
    file_queue = Queue()
    running = False

    @staticmethod
    def check_dir(dir_path):
        if not os.path.exists(dir_path):
            raise CourseHelperException(f'文件夹"{dir_path}"不存在')
        return True

    @staticmethod
    def _get_file_name(file_name_raw: str) -> str:
        file_name = (
            file_name_raw.encode("unicode_escape").decode("utf-8").replace("\\x", "%")
        )
        file_name = parse.unquote(file_name, encoding="gbk")
        pos = file_name.find('filename="')
        return file_name[pos + len('filename="'): -1]

    @staticmethod
    def _byte_to_suitable_size(byte_size: int):
        if byte_size <= 1024:
            return f'{byte_size}B'
        elif byte_size <= 1024 ** 2:
            return f'{round(byte_size / 1024, 2)}KB'
        elif byte_size <= 1024 ** 3:
            return f'{round(byte_size / 1024 ** 2, 2)}M'
        else:
            return f'{round(byte_size / 1024 ** 3, 2)}G'

    @staticmethod
    def _sec_to_suitable_time(sec: int):
        return time.strftime("%H:%M:%S", time.gmtime(sec))

    @classmethod
    async def get_file_info(cls, session: Session, file_id, res_id):
        """
        获取下载文件名、大小等信息
        """
        try:
            with session.get(
                    f'https://course2.xmu.edu.cn/meol/common/script/download.jsp?fileid={file_id}&resid={res_id}',
                    stream=True) as r:
                content_size = int(r.headers['content-length'])
                file_name = cls._get_file_name(r.headers.get("Content-Disposition"))
                file_name_no_ext = file_name[0:file_name.rfind('.')]

                file_ext = file_name[file_name.rfind('.') + 1:].lower()
                file_name = f'{file_name_no_ext}.{file_ext}'
                file_size = cls._byte_to_suitable_size(content_size)
                return {
                    'success': True,
                    'file_name': file_name,
                    'file_ext': file_ext,
                    'file_size': file_size,
                    'file_size_raw': content_size
                }
        except:
            return {'success': False}

    @classmethod
    async def _update_download_progress(cls, download_id: str, speed_str: str, time_remain_str: str,
                                        down_size: int):
        """
        发送ws消息更新前端的下载进度
        """
        await ConnectionManager.send_message({
            'cmd': 'update_download_progress',
            'params': {
                'download_id': download_id,
                'speed': speed_str,
                'time_remain': time_remain_str,
                'down_size': cls._byte_to_suitable_size(down_size),
                'down_size_raw': down_size
            }
        }, client_id=tuple(ConnectionManager.active_connections.keys())[0])

    @classmethod
    async def _download_finished(cls, download_id: str):
        """
        发送ws消息更新前端的下载进度
        """
        await ConnectionManager.send_message({
            'cmd': 'update_download_progress',
            'params': {
                'download_id': download_id,
                'finished': True
            }
        }, client_id=tuple(ConnectionManager.active_connections.keys())[0])

    @classmethod
    async def download_file(cls, download_id: str, file_id: str, res_id: str, path: str):
        """
        提交下载任务到队列
        """
        cls.file_queue.put({
            'download_id': download_id,
            'file_id': file_id,
            'res_id': res_id,
            'path': path
        })
        # 开启下载队列，不等待结果
        asyncio.Task(cls.run())

    @classmethod
    async def run(cls):
        # 判断队列是否已在下载
        if cls.running:
            return

        # 标识正在下载
        cls.running = True
        while True:
            if Downloader.file_queue.empty():
                break
            file_info = Downloader.file_queue.get()

            s = await User.get_login_session()
            with s.get('https://course2.xmu.edu.cn/meol/common/script/download.jsp?'
                       f'fileid={file_info["file_id"]}&resid={file_info["res_id"]}', stream=True) as r:
                file_size = int(r.headers['content-length'])  # 文件大小 Byte
                download_id = file_info['download_id']
                with open(file_info['path'], "wb") as file:
                    down_size = 0  # 已下载字节数
                    old_down_size = 0  # 上一次已下载字节数
                    now = time.time()
                    for chunk in r.iter_content(chunk_size=1024):  # 每次下载1B
                        if chunk:
                            file.write(chunk)
                            down_size += len(chunk)
                            if time.time() - now >= 1:  # 每1s计算一次下载速度
                                speed = down_size - old_down_size
                                time_remain = round((file_size - down_size) / speed)
                                speed_str = cls._byte_to_suitable_size(speed) + '/s'
                                time_remain_str = cls._sec_to_suitable_time(time_remain)

                                # ws发送消息更新下载进度
                                await cls._update_download_progress(download_id, speed_str,
                                                                    time_remain_str, down_size)
                                # 避免阻塞ws通知的线程
                                await asyncio.sleep(1)
                                old_down_size = down_size
                                now = time.time()
                # 此文件下载结束ws消息
                await cls._download_finished(download_id)
                cls.running = False