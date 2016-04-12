#!/usr/bin/env python
# encoding: utf-8
import os

from fabric.api import settings, cd, run, env, put, local

env.hosts = ['root@RealserverNet1', 'root@172.17.0.1']

BASE_DIR = os.path.dirname(__file__)
remote_dir = '/opt/crawler/'

def pack():
    tar_files = ['*.py', 'supervisord.conf']
    local('rm -f /tmp/crawler.tar.gz')
    with cd(BASE_DIR):
        local('tar -czvf /tmp/crawler.tar.gz --exclude=\'*.tar.gz\' --exclude=\'fabfile.py\' %s' % ' '.join(tar_files))


def put_code():
    """
    上传代码
    """
    pack()
    remote_tmp_tar = '/tmp/crawler.tar.gz'
    with cd("/opt/"):
        with settings(warn_only=True):
            run('rm -f %s' % remote_tmp_tar)
            run("rm -fr %s"%remote_dir)
        run('mkdir %s' % remote_dir)
        put('/tmp/crawler.tar.gz', remote_tmp_tar)

        with cd(remote_dir):
            run('tar -xzvf %s' % remote_tmp_tar)
            run("supervisorctl -c supervisord.conf reload")
            run("supervisorctl -c supervisord.conf status")

        with settings(warn_only=True):
            run('rm -f %s' % remote_tmp_tar)
    local('rm -f /tmp/crawler.tar.gz')


def status():
    with cd(remote_dir):
        run("supervisorctl -c supervisord.conf status")