# coding: utf-8

import os
import xmlrpclib
import argparse
import xml.etree.ElementTree as ET

PARSER = argparse.ArgumentParser(
    description="Generate Payroll PDF and Cancel XML")
PARSER.add_argument("-d", "--db", help="DataBase Name", required=True)
PARSER.add_argument("-r", "--user", help="OpenERP User", required=True)
PARSER.add_argument("-w", "--passwd", help="OpenERP Password", required=True)
PARSER.add_argument("-p", "--port",
                    type=int,
                    help="Port, 8069 for default", default="8069")
PARSER.add_argument("-s", "--server",
                    help="Server IP, 127.0.0.1 for default",
                    default="127.0.0.1")
PARSER.add_argument("-dir", "--directory", help="XML Directory path",
                    required=True)
ARGS = PARSER.parse_args()

if ARGS.db is None or ARGS.user is None or ARGS.passwd is None or ARGS.directory is None:
    print "Must be specified DataBase, User, Password and Directory path"
    quit()

DB_NAME = ARGS.db
USER = ARGS.user
PASSWD = ARGS.passwd
SERVER = ARGS.server
PORT = ARGS.port
URL = 'http://%s:%s' % (SERVER, PORT)
XML_DIR = ARGS.directory
common = xmlrpclib.ServerProxy('{}/xmlrpc/2/common'.format(URL))
UID = common.authenticate(DB_NAME, USER, PASSWD, {})

hr_payslip = xmlrpclib.ServerProxy('{}/xmlrpc/2/object'.format(URL))
hr_id = hr_payslip.execute_kw(DB_NAME, UID, PASSWD, 'hr.payslip', 'search',
                              [[]], {'limit': 1})[0]

for filename in os.listdir(XML_DIR):
    if not filename.endswith('.xml'):
        continue
    hr_copy = hr_payslip.execute_kw(DB_NAME, UID, PASSWD, 'hr.payslip', 'copy',
                                    [hr_id])