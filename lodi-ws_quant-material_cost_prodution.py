# !/usr/bin/env python
# -*- coding: utf-8 -*-
import oerplib
import logging
import datetime
import click
import csv
import psycopg2
from pprint import pprint
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
    conn_pg = psycopg2.connect(database=dbo, user=du, password=dp)
    update_material_cost(connect, conn_pg, 'inventory')
    update_material_cost(connect, conn_pg, 'supplier')
    update_material_cost_in_production(connect, conn_pg)
    return True


def update_material_cost(connect, conn_pg, where):
    cr = conn_pg.cursor()
    cr.execute(QUERY_MATERIAL.format(where=where))
    move_ids = cr.fetchall()
    while move_ids:
        print len(move_ids), where
        move_id = move_ids.pop()
        move_id = move_id[0]
        cr.execute(
            '''
            SELECT sq.id, sq.cost
            FROM stock_quant_move_rel AS sqm_rel
            INNER JOIN stock_quant AS sq ON sq.id = sqm_rel.quant_id
            WHERE sqm_rel.move_id = {move_id}
            '''.format(move_id=move_id)
            )
        quant_ids = cr.fetchall()
        for quant_tuple in quant_ids:
            quant_id, cost = quant_tuple
            cr.execute('''
                UPDATE stock_quant
                SET material_cost = {material_cost}
                WHERE id = {id}
                    '''.format(material_cost=cost, id=quant_id))
            conn_pg.commit()

    return True


def get_dag_production(connect, conn_pg):
    res = {}
    cr = conn_pg.cursor()

    cr.execute('''
        SELECT id FROM mrp_production WHERE state = 'done'
            ''')
    production_ids = ', '.join(str(val[0]) for val in cr.fetchall())

    if not production_ids:
        return res

    cr.execute('''
        SELECT
            mp1.id AS pr1,
            sm2.production_id AS pr2
        FROM mrp_production as mp1
        INNER JOIN stock_move AS sm1 ON sm1.raw_material_production_id = mp1.id
        INNER JOIN stock_quant_move_rel AS sqm_rel1 ON sqm_rel1.move_id = sm1.id
        INNER JOIN stock_quant_move_rel AS sqm_rel2 ON sqm_rel2.quant_id = sqm_rel1.quant_id
        INNER JOIN stock_move AS sm2 ON sm2.id = sqm_rel2.move_id
        WHERE
        sm2.production_id IN ({production_ids})
        AND mp1.id IN ({production_ids})
            '''.format(production_ids=production_ids))
    result = cr.fetchall()

    for pr1, pr2 in result:
        pr1, pr2 = str(pr1), str(pr2)
        if not res.get(pr1):
            res[pr1] = set([pr2])
            continue
        res[pr1].add(pr2)

    dag = dagger.dagger()
    for key, val in res.iteritems():
        dag.add(key, list(val))
    dag.run()
    res = dag.ordernames()
    res = res.split(',')
    res = [int(val) for val in res]

    return res


def update_material_cost_in_production(connect, conn_pg):
    cr = conn_pg.cursor()
    cr.execute('''
        SELECT id FROM mrp_production WHERE state = 'done'
            ''')
    production_all_ids = [val[0] for val in cr.fetchall()]

    production_ids = get_dag_production(connect, conn_pg)
    production_ids.reverse()
    production_remain_ids = list(set(production_all_ids) - set(production_ids))
    production_all_ids = production_ids + production_remain_ids

    while production_all_ids:
        print len(production_all_ids), 'production'
        production_id = production_all_ids.pop()
        grand_total = 0.0
        produced_qty = 0.0

        # Find produced goods
        cr.execute('''
            SELECT id FROM stock_move
            WHERE production_id = {production_id}
            '''.format(production_id=production_id))
        produced_ids = ', '.join(str(val[0]) for val in cr.fetchall())

        cr.execute('''
            SELECT quant_id FROM stock_quant_move_rel
            WHERE move_id IN ({produced_ids})
            '''.format(produced_ids=produced_ids))
        produced_quant_ids = ', '.join(str(val[0]) for val in cr.fetchall())

        cr.execute('''
            SELECT material_cost, qty, id FROM stock_quant
            WHERE id IN ({produced_quant_ids})
            '''.format(produced_quant_ids=produced_quant_ids))
        produced_quant_vals = cr.fetchall()

        for quant_val in produced_quant_vals:
            produced_qty += quant_val[1]

        # Find consumed raw material
        cr.execute('''
            SELECT id FROM stock_move
            WHERE raw_material_production_id = {production_id}
            '''.format(production_id=production_id))
        consumed_ids = ', '.join(str(val[0]) for val in cr.fetchall())
        if not consumed_ids:
            # TODO: Record when there is a production without consumption
            continue

        cr.execute('''
            SELECT quant_id FROM stock_quant_move_rel
            WHERE move_id IN ({consumed_ids})
            '''.format(consumed_ids=consumed_ids))
        consumed_quant_ids = ', '.join(str(val[0]) for val in cr.fetchall())
        if not consumed_quant_ids:
            # TODO: Record when there is a production without consumption
            continue

        cr.execute('''
            SELECT material_cost, qty FROM stock_quant
            WHERE id IN ({consumed_quant_ids})
            '''.format(consumed_quant_ids=consumed_quant_ids))
        consumed_quant_vals = cr.fetchall()

        for quant_val in consumed_quant_vals:
            grand_total += quant_val[0] * quant_val[1]

        # BEWARE: some material_cost could already exist?
        material_cost_unit = grand_total / produced_qty

        for quant_val in produced_quant_vals:
            cr.execute('''
                UPDATE stock_quant
                SET material_cost = {material_cost}
                WHERE id = {id}
                    '''.format(
                    material_cost=quant_val[1] * material_cost_unit,
                    id=quant_val[2]))
            conn_pg.commit()


if __name__ == '__main__':
    run()
