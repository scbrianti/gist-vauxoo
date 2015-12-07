# !/usr/bin/env python
# -*- coding: utf-8 -*-
import oerplib
import logging
import click
import psycopg2

_logger = logging.getLogger(__name__)
#############################
# ## Constants Declaration ###
#############################


@click.command()
@click.option('-dbo', default='test',
              prompt='Database Odoo', help='DB Name')
@click.option('-uo', default='admin', prompt='User Odoo', help='User of odoo')
@click.option('-po', default='admin', prompt='Password of Odoo',
              help='Password of user Odoo')
@click.option('-pod', default=8069, prompt='Port Odoo', help='Port of Odoo')
@click.option('-du', default='None', prompt='Database User',
              help='Name of database user')
@click.option('-dp', default='None', prompt='Database Password',
              help='Password of database user')
@click.option('-dpo', default=5432, prompt='Database Port',
              help='Port of Postgres')
@click.option('-dh', default='None', prompt='Database Host',
              help='Host of Postgres')
def run(
        dbo, uo, po, pod, dpo, du=None, dp=None, dh=None):
    if du == 'None':
        du = None
    if dp == 'None':
        dp = None
    if dh == 'None':
        dh = None

    connect = oerplib.OERP('localhost', port=pod, timeout=3600)
    connect.login(user=uo, passwd=po, database=dbo)
    conn_pg = psycopg2.connect(database=dbo, user=du, password=dp, host=dh)
    get_ready_workcenter_production(connect, conn_pg)
    return True


def get_ready_workcenter_production(connect, conn_pg):
    cr = conn_pg.cursor()
    cr.execute("""
        SELECT id FROM mrp_production WHERE state in ('done', 'confirmed',
        'ready', 'in_production')
            """)
    production_all_ids = [val[0] for val in cr.fetchall()]

    initial_len = len(production_all_ids)
    while production_all_ids:
        print '%s / %s' % (len(production_all_ids), initial_len)
        production_id = production_all_ids.pop()
        connect.execute(
            'mrp.production', 'ws_set_routing_workcenter', production_id)
    return True


if __name__ == '__main__':
    run()
