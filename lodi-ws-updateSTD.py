# !/usr/bin/env python
# -*- coding: utf-8 -*-
import oerplib
import logging
import click
import psycopg2

logging.basicConfig(
    format='%(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p',
    filename='lodi-ws-updateSTD.log', level=logging.INFO)
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
    update_std_price(connect, conn_pg)
    return True


def get_products(connect, conn_pg):
    """Return all products which represent top parent in bom
    [x]---+   [y]
     |    |  / |
     |    | /  |
    [a]  [b]  [c]
     |  / |
     | /  |
    [t]  [u]
    That is x and y
    """
    cr = conn_pg.cursor()

    cr.execute('''
        SELECT
        DISTINCT mb.product_tmpl_id AS pp1,
                pp.product_tmpl_id AS pp2
        FROM mrp_bom AS mb
        INNER JOIN mrp_bom_line as mbl ON mbl.bom_id = mb.id
        INNER JOIN product_product as pp ON pp.id = mbl.product_id
        WHERE mb.active = True
        ORDER BY pp1;
            ''')
    result = cr.fetchall()
    parents = set([r[0] for r in result if r[0] is not None])
    children = set([r[1] for r in result if r[1] is not None])
    root = list(parents - children)

    cr.execute('''
        SELECT DISTINCT id
        FROM product_product
        WHERE product_tmpl_id IN %s''', (tuple(root),))
    root = cr.fetchall()
    return list(set(res[0] for res in root))


def update_std_price(connect, conn_pg):
    product_ids = get_products(connect, conn_pg)
    if not product_ids:
        _logger.info('No Products to Update')
        return True

    total = len(product_ids)
    _logger.info('%s products are going to be updated', total)

    count = 0
    for product in product_ids:
        count += 1
        _logger.info(
            'ID: \t%s is being updated. \t%s \tof \t%s', product, count, total)
        connect.execute(
            'wizard.price', 'execute_cron', [product])
    return True


if __name__ == '__main__':
    run()
