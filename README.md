py-kill 属于简易版的 pt-kill 工具

Python 3.6 编写，主要是弥补 pt-kill 工具貌似不支持 SQL 进程状态为 execute 时的处理，或者我对 pt-kill 的使用方式有误。另外就是增加了邮件报警。

特性：
1. 支持后台或前台运行
2. 支持邮件报警
3. 支持多线程监控
4. pt-kill常规选项也都支持

支持的选项：

使用方式：

python3 py-kill.py --instance="172.16.10.10:3306" --user=root --password="123456" --match-command="query|execute" --match-info="^select" --interval=1 --busy-time=60 --victims=all --kill --from_addr="test@163.com" --from_pass='123456' --smtp_server='mail.163.com' --to_addr='test@163.com'
