#!/usr/bin/env python
# encoding: utf-8
import json
import os
from bs4 import BeautifulSoup
import fcntl
import config
import base64
import pika.connection
import logging
import urlparse
from base import ParseBase


class ParseUrl(ParseBase):
    def parse_item(self, message):
        message = json.loads(message)
        f = open(message.get("path"), "r")
        url = base64.b64decode(os.path.basename(message.get("path")))
        # todo 检测锁
        fcntl.flock(f.fileno(), fcntl.LOCK_EX)

        soup = BeautifulSoup(f, "html.parser")
        fcntl.flock(f.fileno(), fcntl.LOCK_UN)
        a_list = soup.find_all("a")
        for a in a_list:
            href = a.get("href")
            if href:
                self.y_urs(href, url)
        logging.info(" [%s] add download queue %s"%(url, len(a_list)))

    def y_urs(self, path, url):
        up = urlparse.urlparse(path)
        if up.scheme and up.scheme not in ["http", "https"]: return
        if not up.netloc:
            up = urlparse.urlparse(urlparse.urljoin(url, path))
            self.channel.basic_publish(exchange="", routing_key=config.DOWNLOAD_QUEUE,
                                       body=up.geturl(), properties=pika.BasicProperties(delivery_mode=2))

    def __init__(self):
        super(ParseUrl, self).__init__()

    def get_queue_name(self):
        return "parse_url"

    def handle_connect(self):
        super(ParseUrl, self).handle_connect()
        self.queue_bind(config.DOWNLOAD_ACK_ROUTING_PREFIX + ".#")
        self.channel.queue_declare(queue=config.DOWNLOAD_QUEUE, durable=True)


class ParseEmail(ParseBase):
    """
    提取页面的email
    """

    def __init__(self):
        super(ParseEmail, self).__init__()

    def handle_connect(self):
        super(ParseEmail, self).handle_connect()
        self.queue_bind(config.DOWNLOAD_ACK_ROUTING_PREFIX + ".#")


if __name__ == "__main__":
    ParseUrl().run()
