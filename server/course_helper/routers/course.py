import asyncio
import os
import re

import nanoid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from lxml import etree
from pydantic import BaseModel

from .user import User
from ..common import success_info, CourseHelperException, error_info
from ..logger import Logger
from ..download import Downloader

router = APIRouter()
logger: Logger


class FileModel(BaseModel):
    file_id: str
    res_id: str
    file_dir: str = './'


class DownloadFilesModel(BaseModel):
    file_list: list[FileModel]
    dir_path: str


class HomeworkSubmitModel(BaseModel):
    hw_id: str
    content: str


@router.on_event("startup")
async def __init():
    #   获取默认日志
    global logger
    logger = Logger('课程模块')


@router.get('/getCourseList')
async def get_course_list():
    """
    获取课程列表
    """
    try:
        session = await User.get_login_session()
        res = session.get('https://course2.xmu.edu.cn/meol/lesson/blen.student.lesson.list.jsp')
        html = etree.HTML(res.text)
        tr_list = html.xpath("//table[@id='table2']//tr")
        tr_list.pop(0)

        course_list = []
        for tr in tr_list:
            td_list = tr.xpath('.//td')

            a = td_list[0].xpath('./a')[0]
            href = a.attrib['href']
            course_list.append({
                'name': a.text.strip(),
                'college': td_list[1].text.strip(),
                'teacher': td_list[2].text.strip(),
                'course_id': href[href.find('?lid=') + 5:]
            })
        return success_info(msg='获取课程列表成功！', data=course_list)

    except CourseHelperException as e:
        logger.warning(f'获取课程列表失败 - 失败原因:{e}')
        raise HTTPException(400, detail=error_info(e.data))
    except Exception as e:
        logger.debug(f'获取课程列表失败 e-{e}')
        raise HTTPException(400, detail=error_info('获取课程列表失败'))


@router.get('/getCourseIntroduction/{course_id}')
async def get_course_introduction(course_id: str):
    """
    获取课程介绍
    """
    try:
        session = await User.get_login_session()
        res = session.get(f'https://course2.xmu.edu.cn/meol/lesson/coursesum.jsp?lid={course_id}')
        html = etree.HTML(res.text)
        nodes = html.xpath("//td[@class='text']//input[@type='hidden']")
        content = nodes[0].attrib['value']
        return success_info(msg='获取课程介绍成功', data={
            'course_id': course_id,
            'content': content
        })

    except CourseHelperException as e:
        logger.warning(f'获取课程介绍失败 - 失败原因:{e}')
        raise HTTPException(400, detail=error_info(e.data))
    except Exception as e:
        logger.debug(f'获取课程介绍失败 e-{e}')
        raise HTTPException(400, detail=error_info('获取课程介绍失败'))


@router.get('/getHomeworkCommittableState')
async def get_homework_committable_state(course_id: str, hw_id: str):
    """
    检查作业可提交状态
    """
    try:
        session = await User.get_login_session()
        session.get(f'https://course2.xmu.edu.cn/meol/jpk/course/layout/newpage/index.jsp?courseId={course_id}')
        res = session.get(f'https://course2.xmu.edu.cn/meol/common/hw/student/hwtask.view.jsp?hwtid={hw_id}')
        html = etree.HTML(res.text)
        return success_info(msg='检验作业可提交状态成功', data={
            'hw_id': hw_id,
            'committable': len(html.xpath("//div[@class='buttonc']/input[@value='提交作业']")) > 0
        })

    except CourseHelperException as e:
        logger.warning(f'检验作业是否可提交失败 - 失败原因:{e}')
        raise HTTPException(400, detail=error_info(e.data))
    except Exception as e:
        logger.debug(f'检验作业是否可提交失败 e-{e}')
        raise HTTPException(400, detail=error_info('检验作业是否可提交失败'))


@router.get('/getCourseHomework/{course_id}')
async def get_course_homework(course_id: str):
    """
    获取课程作业
    """
    try:
        session = await User.get_login_session()
        session.get(f'https://course2.xmu.edu.cn/meol/jpk/course/layout/newpage/index.jsp?courseId={course_id}')
        res = session.get('https://course2.xmu.edu.cn/meol/common/hw/student/hwtask.jsp')
        html = etree.HTML(res.text)
        nodes: list = html.xpath("//table[@class='valuelist']//tr")
        nodes.pop(0)

        homeworks = []
        for node in nodes:
            cols = node.xpath("./td")
            ele_a = cols[0].xpath("./a[1]")[0]
            hw_obj = {
                'hw_id': ele_a.attrib['href'][ele_a.attrib['href'].find('=') + 1:],
                'title': ele_a.text.strip()
            }

            for index, name in enumerate(['end_date', 'score', 'publisher'], 1):
                hw_obj[name] = cols[index].text.strip()

            #   无法继续提交则为false（可能是超时、不可重复提交）
            hw_obj['committable'] = len(cols[5].xpath('./a')) > 0
            homeworks.append(hw_obj)

        return success_info(msg='获取课程作业成功', data={
            'course_id': course_id,
            'homeworks': homeworks
        })

    except CourseHelperException as e:
        logger.warning(f'获取课程作业失败 - 失败原因:{e}')
        raise HTTPException(400, detail=error_info(e.data))
    except Exception as e:
        logger.debug(f'获取课程作业失败 e-{e}')
        raise HTTPException(400, detail=error_info('获取课程作业失败'))


@router.get('/getHomeworkDetails/{hw_id}')
async def get_homework_details(hw_id: str):
    """
    获取作业详情
    """
    try:
        session = await User.get_login_session()
        res = session.get(f'https://course2.xmu.edu.cn/meol/common/hw/student/taskanswer.jsp?hwtid={hw_id}')
        html = etree.HTML(res.text)

        content = {}
        tables = html.xpath("//table[@class='infotable']")

        for index, name in enumerate(['title', 'end_date', 'scoring_method', 'score'], 1):
            content[name] = tables[0].xpath(f".//tr[{index}]/td")[0].text.strip()

        content['scoring_method'] = content['scoring_method'].replace('打分制:', '')

        nodes = (
            tables[0].xpath(".//tr[5]/td/input"),
            tables[1].xpath('.//tr[2]/td/input'),
            tables[2].xpath('.//tr[2]/td/input'),
        )
        names = ('content', 'answer', 'result', 'comment')

        for index in range(3):
            if len(nodes[index]) > 0:
                value = re.sub(r"(http.*/meol|/meol)(.*?openfile.jsp\?id=)",
                               "http://127.0.0.1:6498/file/openFile/",
                               nodes[index][0].attrib['value'])

                value = re.sub(r'<a href=.*?openFile/(.*?)">(.*?)</a>',
                               r'''<a href="javascript:void(0);" fid="\g<1>">\g<2></a>''',
                               value)

                content[names[index]] = value
            else:
                content[names[index]] = ''

        content['comment'] = tables[3].xpath('.//tr[2]/td')[0].text.strip()

        return success_info(msg='获取课程作业成功', data={
            'hw_id': hw_id,
            'content': content
        })

    except CourseHelperException as e:
        logger.warning(f'获取作业详情失败 - 失败原因:{e}')
        raise HTTPException(400, detail=error_info(e.data))
    except Exception as e:
        logger.debug(f'获取作业详情失败 e-{e}')
        raise HTTPException(400, detail=error_info('获取课程详情失败'))


@router.post('/submitHomework')
async def submit_homework(data: HomeworkSubmitModel):
    try:
        session = await User.get_login_session()
        res = session.post('https://course2.xmu.edu.cn/meol/common/hw/student/write.do.jsp', {
            'hwtid': data.hw_id,
            'IPT_BODY': data.content.encode('gbk'),
        }, allow_redirects=False)

        if res.status_code != 302:
            raise CourseHelperException('作业提交失败')

        return success_info('作业提交成功')
    except CourseHelperException as e:
        logger.warning(f'作业提交失败 - 失败原因:{e}')
        raise HTTPException(400, detail=error_info(e.data))
    except Exception as e:
        logger.debug(f'作业提交失败 e-{e}')
        raise HTTPException(400, detail=error_info('作业提交失败'))


@router.get('/getCourseResource/{course_id}')
async def get_course_resource(course_id: str, folder_id: str = '0', deep: bool = False):
    """
    获取课程资源树状结构
    """
    try:
        session = await User.get_login_session()
        content = get_resource_in_folder(course_id, folder_id, session, deep_flag=deep)
        return success_info(msg='获取课程资源成功', data={
            'course_id': course_id,
            'content': content
        })

    except CourseHelperException as e:
        logger.warning(f'获取课程资源失败 - 失败原因:{e}')
        raise HTTPException(400, detail=error_info(e.data))
    except Exception as e:
        logger.debug(f'获取课程资源失败 e-{e}')
        raise HTTPException(400, detail=error_info('获取课程资源失败'))


@router.get('/getCourseResourceInfo')
async def get_course_resource_info(file_id: str, res_id: str):
    """
    获取课程资源信息: 文件名、文件大小
    """
    try:
        session = await User.get_login_session()
        res = session.get('https://course2.xmu.edu.cn/meol/common/script/preview/'
                          f'download_preview.jsp?fileid={file_id}&resid={res_id}')
        html = etree.HTML(res.text)
        elements = html.xpath('//div[@class="h1-title"]//span')
        info = {
            'file_name': elements[1].text.strip(),
            'file_size': elements[2].text.strip().strip('()\n')
        }
        return success_info('获取课程资源信息成功', data=info)

    except CourseHelperException as e:
        logger.warning(f'获取课程资源信息失败 - 失败原因:{e}')
        raise HTTPException(400, detail=error_info(e.data))
    except Exception as e:
        logger.debug(f'获取课程资源信息失败 e-{e}')
        raise HTTPException(400, detail=error_info('获取课程资源信息失败'))


@router.post('/downloadCourseResource')
async def download_course_resource(data: DownloadFilesModel, background_tasks: BackgroundTasks):
    """
    下载课程资源文件
    """
    try:
        session = await User.get_login_session()

        file_list = data.file_list
        download_info = []

        for item in file_list:
            file_info = await Downloader.get_file_info(session, item.file_id, item.res_id)
            if file_info['success']:
                while True:
                    # 拼接目录 子目录 文件名
                    file_path = os.path.abspath(os.path.join(data.dir_path, item.file_dir, file_info['file_name']))
                    if os.path.exists(file_path):
                        # 文件名重复则添加一个#
                        file_name_no_ext = file_info['file_name'][0:file_info['file_name'].rfind('.')]
                        file_info['file_name'] = f"{file_name_no_ext}#.{file_info['file_ext']}"
                    else:
                        break

                download_id = nanoid.generate()
                file_info['download_id'] = download_id
                file_info['file_path'] = file_path
                # 提交BackgroundTasks 避免阻塞当前进程
                background_tasks.add_task(
                    Downloader.add_download_task, download_id, item.file_id, item.res_id, file_path
                )
                await asyncio.sleep(0.01)  # 避免阻塞ws通知的线程
                download_info.append(file_info)
                logger.success(f'下载任务创建成功 download_id:{download_id} size:{file_info["file_size"]} path:{file_path}')
                # 降低请求频率
                await asyncio.sleep(0.35)

        # 1s后开启下载队列（通知消费者）
        async def tmp():
            await asyncio.sleep(1)
            await Downloader.run()

        background_tasks.add_task(tmp)

        return success_info('文件已添加到下载列表', data=download_info)

    except CourseHelperException as e:
        logger.warning(f'文件下载失败 - 失败原因:{e}')
        raise HTTPException(400, detail=error_info(e.data))
    except Exception as e:
        logger.debug(f'文件下载失败 e-{e}')
        raise HTTPException(400, detail=error_info('文件下载失败'))


def get_resource_in_folder(course_id, folder_id, s, deep_flag=False) -> list:
    """
    递归获取课程资源树状结构
    """
    res = s.get(f'https://course2.xmu.edu.cn/meol/common/script/listview.jsp?folderid={folder_id}&lid={course_id}')
    html = etree.HTML(res.text)
    nodes: list = html.xpath("//table[@class='valuelist']//tr")
    content = []
    for row in nodes:
        # 表头栏跳过（可能出现多个表头）
        if len(row.xpath("./th")) > 0:
            continue
        img_url = row.xpath(".//img")[0].attrib['src']
        type_name = img_url[img_url.rfind('/') + 1:img_url.rfind('.')]
        res_ele = row.xpath(".//a")[0]
        res_url = res_ele.attrib['href']
        res_name = res_ele.text.strip()

        res_obj = {'type_name': type_name, 'res_name': res_name, 'key': nanoid.generate()}
        if type_name == 'folder':
            res_obj['folder_id'] = re.search(r'folderid=(\d*)', res_url).group(1)
            if deep_flag:
                res_obj['children'] = get_resource_in_folder(course_id, res_obj['folder_id'], s, deep_flag)
        elif type_name == 'link':
            res_id = re.search(r'resid=(\d*)', res_url).group(1)
            link_res = s.get(f'https://course2.xmu.edu.cn/meol/common/script/openurl.jsp?resid={res_id}')
            res_obj['link'] = re.search(r"location.href='(.*?)'", link_res.text).group(1)
        else:
            res_obj['file_id'], res_obj['res_id'] = re.search(r'fileid=(\d*).*?resid=(\d*)', res_url).group(1, 2)
        content.append(res_obj)
    return content
