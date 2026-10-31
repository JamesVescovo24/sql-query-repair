"""Pure Python SQL outcome oracle; never executes SQL or imports sqlite3/LLMs."""
import json
import re
from contract import Tool
from .checks import result, read_receipt
CASES=('region-revenue','overdue-count')

def _row_strings(data):
    return sorted(json.dumps(row,ensure_ascii=False,separators=(',',':')) for row in data)

def _fixture_expected(case,fixture):
    customers={c.customer_id:c.region for c in fixture.customers}
    orders={o.order_id:o for o in fixture.orders}
    totals={}
    if case=='region-revenue':
        ids=set()
        for p in fixture.payments:
            if p.payment_id in ids or p.order_id not in orders:
                return None
            ids.add(p.payment_id)
            region=customers.get(orders[p.order_id].customer_id)
            if region is None:
                return None
            totals[region]=totals.get(region,0)+p.amount_cents
        cols=['region','total_cents']
    elif case=='overdue-count':
        if len(orders)!=len(fixture.orders):
            return None
        for o in fixture.orders:
            if o.customer_id not in customers:
                return None
            if o.status=='OPEN' and o.due_date<'2026-10-01':
                region=customers[o.customer_id]
                totals[region]=totals.get(region,0)+1
        cols=['region','overdue_orders']
    else:
        return None
    if len(customers)!=len(fixture.customers):
        return None
    return {'label':fixture.label,'columns':cols,'rows':_row_strings([[region,value] for region,value in totals.items()])}

def _results_as_dict(results):
    return [{'label':r.label,'columns':r.columns,'rows':r.rows} for r in results]

def _expected(case,fixtures):
    if len(fixtures)!=3 or len({f.label for f in fixtures})!=3:
        return None
    expected=[_fixture_expected(case,x) for x in fixtures]
    if any(x is None for x in expected):
        return None
    return expected

def _valid_results(given, expected):
    if not isinstance(given,list) or len(given)!=len(expected):
        return False
    for obj,exp in zip(given,expected):
        if not isinstance(obj,dict) or set(obj)!={'label','columns','rows'}:
            return False
        if obj != exp:
            return False
        if len(obj['rows'])>500:
            return False
    return True

def _sql_ok(sql):
    return isinstance(sql,str) and 0<len(sql)<=3000 and re.match(r'^\s*SELECT\b',sql,re.I) is not None and not any(x in sql for x in (';','--','/*','*/'))

def verify_input(tool,value):
    ok=value.case in CASES and type(value.seed) is int and 1 <= value.seed <= 10000
    if tool==Tool.SAVE:
        ok=ok and _sql_ok(value.sql)
    return result(ok,'known SQL case' if ok else 'unsupported case, seed, or unsafe SQL')

def verify_output(tool,input_value,output_value,workspace):
    if tool==Tool.READ:
        ok=output_value.case==input_value.case and output_value.seed==input_value.seed and bool(output_value.broken_query) and bool(output_value.requirement)
        return result(ok,'query description provided')
    if tool==Tool.PIN:
        expected=_expected(output_value.case,output_value.fixtures)
        ok=expected is not None and output_value.case==input_value.case and output_value.seed==input_value.seed and _valid_results(_results_as_dict(output_value.expected),expected)
        return result(ok,'reference independently recomputed' if ok else 'reference inconsistent')
    payload,problem=read_receipt(workspace,output_value)
    required={'case':input_value.case,'seed':input_value.seed,'sql':input_value.sql,'results':_results_as_dict(output_value.results)}
    ok=not problem and payload==required and output_value.case==input_value.case and output_value.seed==input_value.seed and output_value.sql==input_value.sql
    return result(ok,'executed-query report saved' if ok else problem or 'reported results differ from saved execution')

def verify_task(arguments,output,reference,workspace):
    if reference is None or reference.case!=arguments.case or reference.seed!=arguments.seed:
        return result(False,'missing or mismatched reference query fixtures')
    if output.case!=arguments.case or output.seed!=arguments.seed or not _sql_ok(output.sql):
        return result(False,'submitted SQL or case invalid')
    expected=_expected(arguments.case,reference.fixtures)
    if expected is None or not _valid_results(_results_as_dict(reference.expected),expected):
        return result(False,'reference SQLite results disagree with independent Python oracle')
    record,problem=read_receipt(workspace,output)
    if problem:
        return result(False,problem)
    if record.get('case')!=arguments.case or record.get('seed')!=arguments.seed or record.get('sql')!=output.sql:
        return result(False,'saved SQL text, seed or case differs from submission')
    if record.get('results')!=_results_as_dict(output.results):
        return result(False,'submitted query results do not match saved receipt')
    if not _valid_results(record.get('results'),expected):
        return result(False,'query returns wrong columns or rows on one or more fixtures',fixtures=3)
    return result(True,'query returned correct columns and row multisets on all 3 independent SQLite fixtures',fixtures=3)
