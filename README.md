# rabbitmq-crawler

**基于rabbitmq 简单的分布式爬虫程序**
![这里写图片描述](http://img.blog.csdn.net/20160413013230410)

##配置
使用supervisor 管理进程

使用fabfile部署代码

#运行
修改fabfile.py env.hosts = ['root@RealserverNet1', 'root@172.17.0.1']
修改config.py RABBITMQ_HOST改成rabbitmq IP
```
fab put_code
```


#依赖
##python
pika,bs4,requests,fabfile
##linux
supervisor,rabbitmq-server
