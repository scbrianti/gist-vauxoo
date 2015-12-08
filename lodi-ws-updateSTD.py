# !/usr/bin/env python
# -*- coding: utf-8 -*-
import oerplib
import logging
import click
import psycopg2
import dagger

QUERY_MATERIAL = '''
    SELECT
        sm.id AS sm_id
    FROM stock_move AS sm
    INNER JOIN
        stock_location AS sl_src ON sm.location_id = sl_src.id
    INNER JOIN
        stock_location AS sl_dst ON sm.location_dest_id = sl_dst.id
    WHERE
        sm.state = 'done' -- Stock Move already DONE
        AND sl_src.usage = '{where}'
        AND sl_dst.usage = 'internal'
'''

QUERY = '''
    SELECT
        DISTINCT(sq.id) AS quant_id
    FROM stock_quant AS sq
    INNER JOIN
        stock_quant_move_rel AS sqm_rel ON sqm_rel.quant_id = sq.id
    INNER JOIN
        stock_move AS sm ON sqm_rel.move_id = sm.id
    INNER JOIN
        stock_location AS sl_src ON sm.location_id = sl_src.id
    INNER JOIN
        stock_location AS sl_dst ON sm.location_dest_id = sl_dst.id
    WHERE
        sm.state = 'done' -- Stock Move already DONE
        AND sl_src.usage != sl_dst.usage -- No self transfers
        AND (
            (sl_src.usage = 'internal' AND sl_dst.usage != 'internal')
            OR (
            sl_src.usage != 'internal' AND sl_dst.usage = 'internal')
        )
        AND sl_src.usage = 'production'
        AND sm.production_id IS NOT NULL;
'''

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


def get_dag_product(connect, conn_pg):
    res = {}
    dag = None
    cr = conn_pg.cursor()

    cr.execute('''
        SELECT
            DISTINCT pt.id AS pt1,
            pt2.id AS pt2
        FROM mrp_production mp
        INNER JOIN product_product AS pp ON pp.id = mp.product_id
        INNER JOIN product_template AS pt ON pt.id = pp.product_tmpl_id
        INNER JOIN mrp_bom AS mb ON mb.product_tmpl_id = pt.id
        INNER JOIN mrp_bom_line AS mbl ON mbl.bom_id = mb.id
        INNER JOIN product_product AS pp2 ON pp2.id = mbl.product_id
        INNER JOIN product_template AS pt2 ON pt2.id = pp2.product_tmpl_id
        WHERE mp.state = 'done';
            ''')
    result = cr.fetchall()

    if not result:
        return res, dag

    for pt1, pt2 in result:
        pt1, pt2 = str(pt1), str(pt2)
        if not res.get(pt1):
            res[pt1] = set([pt2])
            continue
        res[pt1].add(pt2)

    dag = dagger.dagger()
    for key, val in res.iteritems():
        dag.add(key, list(val))
    dag.run()
    res = dag.ordernames()
    res = res.split(',')
    res = [int(val) for val in res]

    return res, dag


def update_std_price(connect, conn_pg):
    product_ids, dag = get_dag_product(connect, conn_pg)
    print len(product_ids)
    context = {}
    values = {
        'real_time_accounting': True,
        'recursive': True}
    count = 0
    for product in product_ids:
        count += 1
        path = dag.pathnames(str(product))
        print '{product} {count} / {total}'.format(
            product=product, count=count, total=len(product_ids))
        if path:
            print product, 'NODE'
            continue
        else:
            print product, 'ROOT'
        context.update({'active_model': 'product.template',
                        'active_id': product})
        wzd_price_id = connect.execute(
            'wizard.price', 'create', values, context)

        connect.execute(
            'wizard.price', 'compute_from_bom', [wzd_price_id], context)
    return True


if __name__ == '__main__':
    run()
