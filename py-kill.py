#!/bin/env python3
# -*-coding:utf-8-*-
# auth: pengdongwen
# date: 2018-07-25

import pymysql
import smtplib
import threading
import logging, argparse
import sys, os, time, signal, re
from email.header import Header
from email.mime.text import MIMEText

lock = threading.Lock()

def usage():
    "Print usage and parse input variables"

    parser = argparse.ArgumentParser()
    exclusive_group = parser.add_mutually_exclusive_group()

    parser.add_argument("--user", "-u", dest="user", action="store",
                        help="username for login mysql")

    parser.add_argument("--password", "-p", dest="password", action="store",
                        help="Password to use when connecting to server")

    parser.add_argument("--host", "-H", dest="host", action="store",
                        help="Host for connecting mysql")

    parser.add_argument("--port", "-P", dest="port", action="store", type=int,
                        help="Port for connecting mysql")

    parser.add_argument('--instance', "-instance", dest='instance', action='append', default=[],
                        help='Instance HOST:PORT:USER:PASSWORD for connecting '
                             'mysql (default [])')

    parser.add_argument("--mail", "-mail", dest="mail", action="store_true", default=False,
                        help="Turn on the mail delivery feature (default False)")

    parser.add_argument("--smtp_server", "-smtp_server", dest="smtp_server", action="store",
                        help="Host for connecting mail server")

    parser.add_argument("--smtp_port", "-smtp_port", dest="smtp_port", action="store",
                        default=25, help="Port for connecting mail server")

    parser.add_argument("--from_addr", "-from_addr", dest="from_addr", action="store",
                        help="Set sender address")

    parser.add_argument("--from_pass", "-from_pass", dest="from_pass", action="store",
                        help="Set sender password")

    parser.add_argument("--to_addr", "-to_addr", dest="to_addr", action="store",
                        help="Set recipient addresses")

    parser.add_argument('--split', "-split", dest='split', action='store',
                        help='Instance parameter separator (default :)')

    parser.add_argument("--log", "-l", dest="log", action="store",
                        help="Print all output to this file when daemonized")

    exclusive_group.add_argument("--daemonize", "-d", dest="daemonize", action="store_true",
                        default=False, help="Fork to the background and detach "
                                            "from the shell (default false)")

    exclusive_group.add_argument("--print", "-print", dest="print", action="store_true",
                        default=False, help="Print a KILL statement for matching "
                                            "queries (default false)")

    parser.add_argument("--interval", "-i", dest="interval", action="store", type=int,
                        default=1, help="How often to check for queries to kill (default 1)")

    parser.add_argument("--busy-time", "-bt", dest="busytime", action="store", type=int, default=1,
                        help="Match queries that have been running for longer than"
                             " this time (default 1)")

    parser.add_argument("--match-command", dest="matchcommand", action="store",
                        default='[^(Binlog Dump|Connect)]',
                        help="Match only queries whose Command matches this SQL "
                             "regex (default [^(Binlog Dump|Connect)])")

    parser.add_argument("--match-host", dest="matchhost", action="store",
                        help="Match only queries whose Host matches this SQL regex")

    parser.add_argument("--match-info", dest="matchinfo", action="store",
                        help="Match only queries whose Info (query) matches this SQL regex")

    parser.add_argument("--match-state", dest="matchstate", action="store",
                        help="Match only queries whose State matches this SQL regex")

    parser.add_argument("--match-db", dest="matchdb", action="store",
                        help="Match only queries whose db (database) matches this SQL regex")

    parser.add_argument("--match-user", dest="matchuser", action="store",
                        help="Match only queries whose User matches this SQL regex")

    parser.add_argument("--victims", dest="victims", action="store", default='oldest',
                        help="Which of the matching queries in each class will be "
                             "killed (default oldest)")

    parser.add_argument("--kill", "-k", dest="kill", action="store_true",
                        default=False, help="Kill the connection for matching "
                                            "queries (default false)")

    parser.add_argument('--version', '-v', action='version', version='%(prog)s V1.0')

    options = parser.parse_args()

    if len(options.instance) == 0:
        if not (options.user and options.password and options.host and options.port):
            parser.error("The --user --password --host --port or --instance options "
                         "cannot be empty")
            sys.exit()
        if options.split:
            parser.error("The --instance and --split options must exist simultaneously")
            sys.exit()
    else:
        for instance in options.instance:
            if re.match(r'(.\d+)$', instance):
                options.split = ':'
                instance = instance.split(options.split)
            else:
                if not options.split:
                    options.split = ':'
                    if options.split in instance:
                        instance = instance.split(options.split)
                    else:
                        parser.error("The --instance and --split options format wrong")
                        sys.exit()
                elif options.split in instance:
                    instance = instance.split(options.split)
                else:
                    parser.error("The --instance and --split options format wrong")
                    sys.exit()

            if len(instance) == 1:
                if not (options.port and options.user and options.password):
                    parser.error("The --instance and --port --user --password options "
                                 "cannot be empty")
                    sys.exit()
                elif options.host:
                    parser.error("The --instance and --port --user --password options "
                                 "cannot be empty, "
                                 "but --host option cannot have a value")
                    sys.exit()
            elif len(instance) == 2:
                if not (options.user and options.password):
                    parser.error("The --instance and --user --password options cannot "
                                 "be empty")
                    sys.exit()
                elif (options.port or options.host):
                    parser.error("The --instance and --user --password options cannot "
                                 "be empty, "
                                 "bug --port or --host options cannot have a value")
                    sys.exit()
            elif len(instance) == 3:
                if not options.password:
                    parser.error("The --instance and --password options cannot be empty")
                    sys.exit()
                elif (options.port or options.host or options.user):
                    parser.error("The --instance and --password options cannot be empty, "
                                 "but --port or --host or --user options cannot have a value")
                    sys.exit()
            elif len(instance) == 4:
                if (options.user or options.password or options.host or options.port):
                    parser.error("The --instance and --host --port --user --password options "
                                 "are mutually exclusive")
                    sys.exit()
            elif len(instance) > 4:
                parser.error("The --instance option format wrong")
                sys.exit()

    if options.daemonize is True:
        if options.print is True:
            parser.error("The --daemonize and --print options are mutually exclusive")
            sys.exit()
    else:
        if options.print is not True:
            options.print = True

    if not isinstance(options.interval, int):
        parser.error("The --interval options requires an integer value")
        sys.exit()

    if options.daemonize is True and options.log is None:
        parser.error("The --daemonize and --log options must exist simultaneously")
        sys.exit()

    if options.log is not None:
        if not os.path.exists(os.path.dirname(options.log)):
            parser.error("The log directory %s is not exists" % (os.path.dirname(options.log)))
            sys.exit()

    if options.from_addr or options.from_pass or options.smtp_server or options.to_addr:
        if not (options.from_addr and options.from_pass and options.smtp_server and options.to_addr):
            parser.error("The --from_addr and --from_pass and "
                         "--smtp_server and --to_addr options must "
                         "exist simultaneously")
            sys.exit()
        else:
            options.mail = True

    return options


class Daemon:
    def daemonize(self):
        #Perform first fork.
        try:
            pid = os.fork()
            if pid > 0:
                # first parent out
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #1 failed: (%d) %s\n" %(e.errno, e.strerror))
            sys.exit(1)

        os.chdir("/")
        os.umask(0)
        os.setsid()

        try:
            pid = os.fork()
            if pid > 0:
                # second parent out
                sys.exit(0)
        except OSError as e:
            sys.stderr.write("fork #2 failed: (%d) %s]n" %(e.errno,e.strerror))
            sys.exit(1)

        "redirect standard file descriptors"
        sys.stdout.flush()
        sys.stderr.flush()
        si = open(os.devnull, 'r')
        so = open(os.devnull, 'a+')
        se = open(os.devnull, 'a+')
        os.dup2(si.fileno(), sys.stdin.fileno())
        os.dup2(so.fileno(), sys.stdout.fileno())
        os.dup2(se.fileno(), sys.stderr.fileno())

    def start(self, *args, **kwarg):
        self.daemonize(*args, **kwarg)
        self.run()

    def run(self):
        "You should override this method when you subclass Daemon"


class DatabaseConn:
    def __init__(self, ip=None, user=None, password=None, db=None, port=None, charset='utf8mb4'):
        self.ip = ip
        self.user = user
        self.password = password
        self.db = db
        self.charset = charset
        self.port = int(port)
        self.con = object

    def __enter__(self):
        self.con = pymysql.connect(
            host=self.ip,
            user=self.user,
            passwd=self.password,
            db=self.db,
            charset=self.charset,
            port=self.port,
            )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.con.close()

    def select_execute(self, sql=None):
        with self.con.cursor() as cursor:
            cursor.execute(sql)
            result = cursor.fetchall()
        return result


class SqlCheckThread(threading.Thread):

    def __init__(self, func, args, name=""):
        '''
        显式的调用父类的初始化函数
        '''
        super(SqlCheckThread, self).__init__()
        self.name = name
        self.func = func
        self.args = args

    def run(self):
        '''
        创建新线程的时候，Thread 对象会调用我们的 ThreadFunc 对象
        这时会用到一个特殊函数 __call__()
        '''
        self.res = self.func(*self.args)


def sqlkill(statement, ip, port, user, password, options):
    while True:
        lock.acquire()
        try:
            # t = time.time()
            with DatabaseConn(
                    ip=ip,
                    port=port,
                    user=user,
                    password=password,
            ) as curosr:
                result = curosr.select_execute(sql=statement)
            # ts = time.time() - t

            if options.kill is not True:
                for s in result:
                    if s[0] is not None:
                        logging.info("%s:%s Print %s %s %s (%s %s sec): %s", \
                                     ip, port, s[0], s[1], s[2], s[3], s[4], s[5])

                        if options.mail:
                            sendmail(from_addr=options.from_addr,
                                     from_pass=options.from_pass,
                                     to_addr=options.to_addr,
                                     smtp_server=options.smtp_server,
                                     smtp_port=options.smtp_port,
                                     ip=ip,
                                     port=port,
                                     info=s)
            else:
                for s in result:
                    if s[0] is not None:
                        with DatabaseConn(
                                ip=ip,
                                port=port,
                                user=user,
                                password=password,
                        ) as curosr:
                            curosr.select_execute(sql="kill %s" % int(s[0]))

                        logging.info("%s:%s KILL %s %s %s (%s %s sec): %s", \
                                     ip, port, s[0], s[1], s[2], s[3], s[4], s[5])

                        if options.mail:
                            sendmail(from_addr=options.from_addr,
                                     from_pass=options.from_pass,
                                     to_addr=options.to_addr,
                                     smtp_server=options.smtp_server,
                                     smtp_port=options.smtp_port,
                                     ip=ip,
                                     port=port,
                                     info=s)
        except Exception as e:
            logging.error(e)
        finally:
            lock.release()
            time.sleep(options.interval)

def loop(statement, conn, options):
    connlen = range(len(conn))
    threads = []
    for i in connlen:
        t = SqlCheckThread(sqlkill, \
                           (statement, \
                            conn[i]['ip'], \
                            conn[i]['port'], \
                            conn[i]['user'], \
                            conn[i]['password'], \
                            options), \
                            sqlkill.__name__)
        t.setDaemon(True)
        threads.append(t)

    for i in connlen:
        # start threads
        threads[i].start()

    for i in connlen:
        # threads to finish
        threads[i].join()

def sqlformat(options):

    DICT_FIELD = dict(
        matchcommand = 'COMMAND REGEXP',
        matchuser = 'USER REGEXP',
        matchinfo = 'INFO REGEXP',
        matchdb = 'DB REGEXP',
        matchstate = 'STATE REGEXP',
        matchhost = 'HOST REGEXP'
    )

    _sql = ''
    for arg in DICT_FIELD.keys():
        val = eval('options.' + '{}'.format(arg))
        if val:
            _sql += 'and ( '
            _sql += "%s '%s'" % (DICT_FIELD[arg], val)
            _sql += ' ) and '
            _sql = _sql.rstrip()[:-3]

    if options.victims == "oldest":
        time = 'MAX(TIME)'
    elif options.victims == 'all':
        time = 'TIME'
    else:
        parser.error("The --victims option value is not valid")
        sys.exit()

    statement = " \
        select ID, DB, USER, COMMAND, %s AS TIME, INFO \
        from information_schema.processlist where \
        TIME >= %d \
        %s" % (time, options.busytime, _sql)
    # print(statement)
    return statement


def sendmail(from_addr, from_pass, smtp_server,
             smtp_port=25, to_addr=None, ip=None,
             port=None, info=None):

    from_addr = from_addr
    from_pass = from_pass
    to_addr = to_addr
    smtp_server = smtp_server
    smtp_port = smtp_port

    try:
        server = smtplib.SMTP(host=smtp_server, port=smtp_port, timeout=3)
    except Exception as e:
        logging.error("邮箱连接失败！{}".format(e))
        return

    try:
        server.login(from_addr, from_pass)
    except Exception as e:
        logging.error("邮箱认证失败！{}".format(e))
        return

    if to_addr is not None:
        msg = MIMEText(
            '<html><body>'
            '<h3>有以下SQL因超时被终止，请确认！！！</h3>'
            '<table border="1">'
            '<tr><th>连接地址</th><th>库名</th><th>用户名</th><th>状态</th><th>时间</th><th>SQL</th></tr>'
            '<tr><td>{}:{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td><td>{}</td></tr>'.format(
                ip, port,
                info[1],
                info[2],
                info[3],
                info[4],
                info[5]) +
            '</table>'
            '</body></html>', 'html', 'utf-8')

        msg['From'] = from_addr
        msg['To'] = to_addr
        msg['Subject'] = Header('超时SQL被终止 FROM {}:{}'.format(ip, port), 'utf-8').encode()

        server.sendmail(from_addr, to_addr.split(','), msg.as_string())
        server.quit()


def sigint_handler(signum, frame):
    print("Bye Bye")
    sys.exit()


def main():
    ''' main func '''

    options = usage()

    if options.mail:
        sendmail(from_addr=options.from_addr,
                 from_pass=options.from_pass,
                 smtp_server=options.smtp_server,
                 smtp_port=options.smtp_port)

    statement = sqlformat(options)
    signal.signal(signal.SIGINT, sigint_handler)

    logging.basicConfig(filename=options.log,
                        format='%(asctime)s %(levelname)s %(message)s',
                        level=logging.INFO)

    conn = []

    if len(options.instance) == 0:
        conn.append({
            'ip': options.host,
            'port': options.port,
            'user': options.user,
            'password': options.password
        })
    else:
        for instance in options.instance:
            instance = instance.split(options.split)
            if len(instance) == 1:
                options.host = instance[0]
            elif len(instance) == 2:
                options.host = instance[0]
                options.port = instance[1]
            elif len(instance) == 3:
                options.host = instance[0]
                options.port = instance[1]
                options.user = instance[2]
            elif len(instance) == 4:
                options.host = instance[0]
                options.port = instance[1]
                options.user = instance[2]
                options.password = instance[3]
            else:
                print("The --instance options value is wrong.")
                sys.exit()

            conninfo = {
                'ip': options.host,
                'port': options.port,
                'user': options.user,
                'password': options.password
            }

            conn.append(conninfo)

    try:
        if options.daemonize is True:
            s = Daemon()
            s.start()
            loop(statement, conn, options)
        else:
            loop(statement, conn, options)
    except Exception as e:
        print(e)
        sys.exit()


if __name__ == "__main__":
    main()