"""
资源网站:https://www.copymanga.com/
"""
from proxyPool.ProxyPool import ProxyPool
from selenium import webdriver
import os
import time
from tqdm import tqdm
import random
import requests
from multiprocessing.pool import ThreadPool
import sys
from PIL import Image
import urllib3
import urllib3.contrib.pyopenssl
import shutil


class CopySpider:
    def __init__(self, website, savepath):
        self.website = website
        self.save_path = savepath
        self.proxy_pool = self._get_ip()
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.159 Safari/537.36 Edg/92.0.902.78',
            'referer': 'https://www.copymanga.com/',
            'sec-ch-ua-mobile':'?0',
            'sec-ch-ua': '"Chromium";v="92", " Not A;Brand";v="99", "Microsoft Edge";v="92"'
        }
        self.count = 0
        self.total = 0

    "工具方法"
    def _get_ip(self):
        """
        获取代理池
        :return:
        """
        proxy_pool = ProxyPool()
        return proxy_pool.get_ip()

    def _get_browser(self):
        """
        获取后台运行的，使用了代理的Chrome浏览器
        :return:
        """
        options = webdriver.ChromeOptions()
        options.add_argument('headless')
        proxy = random.choice(self.proxy_pool)['http']
        options.add_argument('–proxy-server='+proxy)
        browser = webdriver.Chrome(options=options)
        return browser

    def _make_dir(self):
        if not os.path.exists(self.save_path):
            os.mkdir(self.save_path)

    def create_breakpoint(self):
        if not os.path.exists(self.save_path + 'breakpoint.txt'):
            with open(self.save_path+'breakpoint.txt', 'w') as f:
                pass
            f.close()

    def _convert_to_pdf(self):
        # 获取对应漫画文件主目录下的所有章节目录
        def get_page_files():
            return os.listdir(self.save_path)

        # 获取章节目录中的图片
        def get_page_photos(page_file):
            return os.listdir(self.save_path + f'\\{page_file}')

        # 获取所有图片
        def get_photos(page_files):
            photos = []
            for file in page_files:
                for photo in get_page_photos(file):
                    photos.append(self.save_path + f'\\{file}\\{photo}')
            return photos

        # 图片转为pdf
        def get_pdf(photos):
            # pdf保存路径
            pdf_path = self.save_path + f'.pdf'

            time.sleep(0.1)
            print('===========开始合成PDF==========')
            count = len(photos)
            img0 = Image.open(photos[0])

            print('===========处理图片==========')
            time.sleep(0.1)
            im_list = []
            for i in tqdm(range(1, count)):
                try:
                    img = Image.open(photos[i])
                    if img.mode == "RGBA":
                        img.mode = 'RGB'
                    im_list.append(img)
                except:
                    continue
            time.sleep(0.1)
            print('===========正式合成PDF==========')
            img0.save(pdf_path, 'pdf', resolution=100.0, save_all=True, append_images=im_list)
            print('===========PDF合成完毕==========')

        get_pdf(get_photos(get_page_files()))

    def _clear(self):
        def delBreakPoint():
            print("===========删除断点文件===========")
            path = self.save_path + 'breakpoint.txt'
            if os.path.exists(path):
                os.remove(path)

        # 删除文件夹
        def delFile(path):
            # 获取目录下的所有文件
            files = os.listdir(path)
            for file in files:
                new_path = path + f'\\{file}'
                # 如果这个文件是文件夹
                if os.path.isdir(new_path):
                    delFile(new_path)
                # 这个文件是文件
                else:
                    os.remove(new_path)
            # 删除自身文件夹
            shutil.rmtree(path, True)

        delBreakPoint()
        delFile(self.save_path)

    "功能方法"
    def _open_website(self):
        # 打开网站页面,并获取需要下载的章节及其序号
        browser = self._get_browser()
        browser.get(self.website)
        chapter_node = browser.find_elements_by_xpath('//*[@id="default全部"]/ul[1]//a')
        chapter_url = []
        orders = []
        print('**********打开网站，获取章节地址**********')
        time.sleep(0.2)
        self.total = len(chapter_node)
        for i in tqdm(range(len(chapter_node))):
            chapter_url.append(chapter_node[i].get_attribute('href'))
            orders.append(i)
        browser.close()
        browser.quit()
        # 检查断点
        print('**********开始检查断点文件**********')
        with open(self.save_path+'breakpoint.txt', 'r') as f:
            while True:
                checked_url = f.readline().replace('\n', '')
                if len(checked_url) == 0:
                    break
                index = chapter_url.index(checked_url)
                del chapter_url[index]
                del orders[index]
                self.count += 1
        print('**********断点文件处理完毕**********')
        f.close()
        page = []
        for i in range(len(chapter_url)):
            page.append([chapter_url[i], orders[i]])
        return page

    def _download_page(self, information):
        """
        下载某一章的内容
        :param information: [page_url, order]
        :return:
        """

        # 获取图片的地址
        def get_photos_url(page_url):
            browser = self._get_browser()
            browser.get(page_url)
            photo_node = browser.find_elements_by_xpath('/html/body/div[1]/div/ul//li/img')
            photo_url = []
            for node in photo_node:
                photo_url.append(node.get_attribute('data-src'))
            browser.close()
            browser.quit()
            return photo_url

        # 获取保存的地址并创建文件夹
        def get_save_path(order):
            if order<10:
                path =  self.save_path + f'\\00{order}'
            elif order<100:
                path = self.save_path + f'\\0{order}'
            else:
                path = self.save_path + f'\\{order}'
            # 创建文件夹
            if not os.path.exists(path):
                os.mkdir(path)
            return path

        # 下载图片到指定文件夹
        def download_photos(photos_url, page_save_path):
            is_downloaded = True
            for i in range(len(photos_url)):
                if i<10:
                    photo_save_path = page_save_path + f'\\00{i}.jpg'
                elif i<100:
                    photo_save_path = page_save_path + f'\\0{i}.jpg'
                else:
                    photo_save_path = page_save_path + f'\\{i}.jpg'
                urllib3.disable_warnings()
                urllib3.contrib.pyopenssl.inject_into_urllib3()
                proxy = random.choice(self.proxy_pool)['http']
                # s = requests.session()
                # s.keep_alive = False
                res = requests.get(photos_url[i], headers=self.headers, proxies={'http': proxy}, verify=False)
                try:
                    res.raise_for_status()
                    open(photo_save_path, 'wb').write(res.content)
                except:
                    print(res.status_code)
                    print(f'下载失败:{photo_save_path}')
                    is_downloaded = False
                    break
            # 判断全部下载完成
            if is_downloaded:
                self.count += 1
                with open(self.save_path + 'breakpoint.txt', 'a') as f:
                    f.writelines(page_url + '\n')
                f.close()

        page_url = information[0]
        order = information[1]
        photos_url = get_photos_url(page_url)
        page_save_path = get_save_path(order)
        download_photos(photos_url, page_save_path)
        # 打印下载完成百分比
        sys.stdout.write('\r%s%%' % format(100 * self.count / self.total, '.2f'))
        sys.stdout.flush()

    def _pool_download(self, informations):
        pool = ThreadPool(10)
        print('下载进度:')
        pool.map(self._download_page, informations)

    "下载主方法"
    def download(self):
        # 创建断点文件
        print('==============创建文件夹==============')
        self.create_breakpoint()
        # 创建存储文件夹
        self._make_dir()
        # 打开漫画网站获取漫画的章节地址
        print('==========获取漫画的章节地址==========')
        website_information = self._open_website()
        # 根据获取的章节地址，获取对应章节的漫画图片
        print('===============开始下载===============')
        self._pool_download(website_information)
        # 将图片合成为一个PDF，并删除之前下载的图片
        print('============图片合成为PDF=============')
        self._convert_to_pdf()
        print('============删除之前下载的文件=============')
        self._clear()


if __name__ == '__main__':
    website = 'https://www.copymanga.com/comic/modujingbingdenuli'
    path = 'd:\\Users\\lcz\\Desktop\\暑期学习\\爬虫\\漫画\\魔都精兵的奴隸'
    copyspider = CopySpider(website, path)
    copyspider.download()