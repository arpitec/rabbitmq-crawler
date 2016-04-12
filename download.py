#!/usr/bin/env python
# encoding: utf-8
import json
import os
import re
import time
import datetime
import config
import fcntl
import logging
import requests
from base import WorkerBase
from urlparse import urlparse
import base64
from bs4 import BeautifulSoup


class Download(WorkerBase):
    def __init__(self):
        super(Download, self).__init__()
        self.download_dir = os.path.join(config.DOWNLOAD_DIR, str(int(time.mktime(datetime.date.today().timetuple()))))
        if not os.path.exists(self.download_dir):
            os.makedirs(self.download_dir)
        self.connect()

    def handle_connect(self):
        # todo 接收config.DOWNLOAD_QUEUE消息 durable持久化
        response = self.channel.queue_declare(queue=config.DOWNLOAD_QUEUE, durable=True)
        logging.info("channel[%s],queue[%s]" % (config.RABBITMQ_HOST, response.method.queue))
        # todo 指定处理消息的方法
        self.channel.basic_consume(self, queue=response.method.queue)
        # todo 定义下载完成的广播
        self.channel.exchange_declare(exchange=config.DOWNLOAD_ACK_TOPIC, type='topic')

    def url_validate(self, url):
        """
            检查URL是否合法
        """
        _url = urlparse(url)
        if not _url.scheme:
            url = "http://" + url
        regex = re.compile(
            r'^(?:http|ftp)s?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+(?:[A-Z]{2,6}\.?|[A-Z0-9-]{2,}\.?)|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        if regex.match(url):
            return url

    def write_file(self, html, url):
        """
        把内容写入文件
        """
        url = base64.b64encode(url)
        p = os.path.join(self.download_dir, url)
        f = open(p, "wb")
        soup = BeautifulSoup(html, "html.parser")
        # todo 写的时候加锁
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)
        f.write(str(soup))
        f.flush()
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        # todo 释放锁
        f.close()
        return p

    def is_exists(self, url):
        url = base64.b64encode(url)
        p = os.path.join(self.download_dir, url)
        return os.path.exists(p)

    def get_html(self, url):
        """
        获取页面内容，模仿浏览器
        """
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64; rv:43.0) Gecko/20100101 Firefox/43.0',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate',
            'Referer': 'http://www.baidu.com',
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
        }
        r = requests.get(url, headers=headers)
        if r.status_code != 200:
            raise IOError(url + ",status_code:%s" % r.status_code)
        return r.text

    def __call__(self, ch, method, properties, body):
        """
            处理每个消息
        """
        try:
            start = time.time()
            url = self.url_validate(body)
            if url and not self.is_exists(body):
                logging.debug("download [%s] start" % body)
                _url = urlparse(url)

                html = self.get_html(url)

                # todo 写入临时文件传递路径给下游解析，必须同一台机器，如果吧数据直接放入队列，消耗太大，暂时在同一台机器上处理
                path = self.write_file(html, body)

                logging.debug("download [%s] complete[%s]" % (url, time.time() - start))
                logging.info("basic_publish:" + config.DOWNLOAD_ACK_ROUTING_PREFIX + "." + _url.netloc)
                """
                    发送下载完成的请求
                    @routing_key 为config.DOWNLOAD_ACK_ROUTING_PREFIX+.+hostname+.+路径
                    config.DOWNLOAD_ACK_ROUTING_PREFIX+".#" 监听所有下载成功的请求,
                    也可以单独监听某个域名如 config.DOWNLOAD_ACK_ROUTING_PREFIX+".www.ip8.me", 有可能多个程序监听
                """
                self.channel.basic_publish(exchange=config.DOWNLOAD_ACK_TOPIC,
                                           routing_key=config.DOWNLOAD_ACK_ROUTING_PREFIX + "." + _url.netloc,
                                           body=json.dumps({"id": self.id, "path": path}))
                ch.basic_ack(delivery_tag=method.delivery_tag)
        except Exception as e:
            logging.error("[" + body + "]" + e.message)
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)



if __name__ == "__main__":
    Download().run()
