#!/usr/bin/env python
# encoding: utf-8
import logging
import os
import signal
import config
import pika
import time
import uuid


class WorkerBase(object):
    def __init__(self):
        self.id = str(uuid.uuid4())
        self.running = True
        self.connection = None
        self.channel = None

    def connect(self):
        """
            建立链接
        """
        while self.running:
            try:
                self.connection = pika.BlockingConnection(pika.ConnectionParameters(host=config.RABBITMQ_HOST))
            except pika.connection.exceptions.ConnectionClosed:
                logging.error("Connection Closed from %s" % config.RABBITMQ_HOST)
                # todo 如果链接中断休眠3秒重新链接,直到链接上
                time.sleep(3)
                continue
            self.channel = self.connection.channel()
            self.handle_connect()
            break

    def handle_connect(self):
        raise NotImplementedError("subclasses of WorkerBase must provide a handle_connect() method")

    def run(self):
        """
            启动
        """
        while self.running:
            try:
                self.channel.start_consuming()
            except (pika.connection.exceptions.ConnectionClosed, IOError) as e:
                # todo 如果链接中断重新链接
                logging.info("start_consuming error %s" % e.message)
                self.connect()

class ParseBase(WorkerBase):
    """
    解析每个页面
    """

    def __init__(self):
        super(ParseBase, self).__init__()
        self.queue_name = self.get_queue_name()
        self.connect()

    def get_queue_name(self):
        return None

    def handle_connect(self):
        self.channel.exchange_declare(exchange=config.DOWNLOAD_ACK_TOPIC, type='topic')
        # todo 当Consumer关闭连接时，这个queue要被deleted。可以加个exclusive的参数。
        result = self.channel.queue_declare(queue=self.queue_name)
        self.queue_name = result.method.queue
        self.channel.basic_consume(self, queue=self.queue_name)

    def queue_bind(self, key):
        """
            绑定事件
        """
        if self.queue_name:
            logging.info("queue[%s] bind[%s]" % (self.queue_name, key))
            self.channel.queue_bind(exchange=config.DOWNLOAD_ACK_TOPIC, queue=self.queue_name, routing_key=key)

    def parse_item(self, message):
        """
        接受到消息，处理的方法
        """
        raise NotImplementedError("subclasses of ParseBase must provide a parse_item() method")

    def __call__(self, ch, method, properties, body):
        """
            处理每个消息
        """
        try:
            self.parse_item(body)
            ch.basic_ack(delivery_tag=method.delivery_tag)
        except:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
