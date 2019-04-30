## py-kill 属于简易版的 pt-kill 工具

Python 3.6 编写，主要是弥补 pt-kill 工具貌似不支持 SQL 进程状态为 execute 时的处理，或者我对 pt-kill 的使用方式有误。另外就是增加了邮件报警。

### 功能：

1. 支持后台或前台运行
2. 支持邮件报警
3. 支持多线程监控
4. pt-kill常规选项也都支持

### 选项：

`--host, -H`：指定连接 MySQL 的地址

`--port, -P`：指定连接 MySQL 的端口

`--user, -u`：指定连接 MySQL 的用户

`--password, -p`：指定连接 MySQL 的用户密码

`--instance, -instance`：有多个实例时，可以使用此选项，默认用冒号分隔，比如"172.18.16.10:3306:root:123456"

`--split, -split`：与--instance配合使用，指定实例中信息的分隔处理方式，默认是:号

`--smtp_server, -smtp_server`：指定邮件服务器地址，可选，如果使用必须与 smtp_port/from_addr/from_pass/to_addr/ 一起使用

`--smtp_port, -smtp_port`：指定邮件服务器端口，可选，如果使用必须与 smtp_port/from_addr/from_pass/to_addr/ 一起使用

`--from_addr, -from_addr`：指定发件人地址，可选，如果使用必须与 smtp_port/from_addr/from_pass/to_addr/ 一起使用

`--from_pass, -from_pass`：指定发件人密码，可选，如果使用必须与 smtp_port/from_addr/from_pass/to_addr/ 一起使用

`--to_addr, -to_addr`：指定收件人地址，可选，如果使用必须与 smtp_port/from_addr/from_pass/to_addr/ 一起使用

`--daemonize, -d`：指定是否开启后台运行模式

`--log, -l`：指定日志文件，必须与 --daemonize 一块使用

`--print, -print`：打印满足条件的SQL语句，也是默认处理方式；当指定了 --log 后，此选项失效

`--kill, -k`：用于 kill 满足条件的SQL语句

`--interval, -i`：指定查询间隔时间，默认1秒

`--busy-time, -bt`：指定超时SQL的阈值，默认1秒

`--victims`：指定满足条件的SQL语句的处理类型，有两个值，oldest 和 all，默认是 oldest，一次只处理一条时间为最大的 SQL 语句，all 表示一次处理所有满足条件的 SQL

`--match-command`：指定要匹配的 command，对应 show processlist 中 command 字段

`--match-host`：指定要匹配的 host，对应 show processlist 中 host 字段

`--match-info`：指定要匹配的 info，对应 show processlist 中 info 字段

`--match-state`：指定要匹配的 state，对应 show processlist 中 state 字段

`--match-db`：指定要匹配的 db，对应 show processlist 中 db 字段

`--match-user`：指定要匹配的 user，对应 show processlist 中 user 字段

`--version, -v`：查看程序版本

参考：https://www.percona.com/doc/percona-toolkit/LATEST/pt-kill.html

### 使用方式：

单实例：
```
$ python3 py-kill.py \
--instance='172.16.10.10:3306' \
--user=root \
--password='123456' \
--match-command='query|execute' \
--match-info='^select' \
--interval=1 \
--busy-time=60 \
--victims='all' \
--print \
--from_addr='test@163.com' \
--from_pass='123456' \
--smtp_server='mail.163.com' \
--smtp_port= 25 \
--to_addr='test@163.com'
```

多实例：

```
$ python3 py-kill.py \
--instance='172.16.10.10:3306:root:123456' \
--instance='172.16.10.11:3306:root:123456' \
--match-command='query|execute' \
--match-info='^select' \
--interval=1 \
--busy-time=60 \
--victims='all' \
--print \
--from_addr='test@163.com' \
--from_pass='123456' \
--smtp_server='mail.163.com' \
--smtp_port= 25 \
--to_addr='test@163.com'
```


