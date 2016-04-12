#!/usr/bin/env python
# encoding: utf-8

"""
    配置文件
"""
import logging
import signal

DOWNLOAD_DIR = "/tmp/page/"
RABBITMQ_HOST = "172.17.42.1"
DOWNLOAD_QUEUE = "download_queue"

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S')

DOWNLOAD_ACK_TOPIC = "download_ack_topic"
DOWNLOAD_ACK_ROUTING_PREFIX = "download_ack"
EXT_SIGNAL = signal.SIGSEGV
PID_PREFIX = "crawler_"
