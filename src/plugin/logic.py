"""SQLite read-only multi-fixture execution and ground-truth pinning."""
from __future__ import annotations
import json
import re
import sqlite3
from dataclasses import asdict
from pathlib import Path
from contract import CaseInput, Customer, Order, Payment, Fixture, FixtureResult, ReadOutput, ReferenceOutput, RunInput, RunOutput
from plugin.datasets import CASES, SCHEMA, RULES, fixtures
from plugin.storage import store

def _case(case,seed):
    if case not in CASES:
        raise ValueError('unknown case: choose region-revenue, overdue-count')
    return CASES[case],fixtures(seed)

def _fixture_models(data):
    return Fixture(data['label'],[Customer(**x) for x in data['customers']],
                   [Order(**x) for x in data['orders']],[Payment(**x) for x in data['payments']])

def _query_fixture(data,sql):
    connection=sqlite3.connect(':memory:')
    try:
        connection.executescript(SCHEMA)
        connection.executemany('INSERT INTO customers VALUES (:customer_id,:region)', data['customers'])
        connection.executemany('INSERT INTO orders VALUES (:order_id,:customer_id,:status,:due_date)', data['orders'])
        connection.executemany('INSERT INTO payments VALUES (:payment_id,:order_id,:amount_cents)', data['payments'])
        # Deny any write after fixture setup (also disallow PRAGMA/ATTACH).
        allowed={sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION}
        connection.set_authorizer(lambda action,*args: sqlite3.SQLITE_OK if action in allowed else sqlite3.SQLITE_DENY)
        actions=[0]
        def guard():
            actions[0]+=1
            return 1 if actions[0]>200 else 0
        connection.set_progress_handler(guard,1000)
        cursor=connection.execute(sql)
        columns=[d[0] for d in cursor.description]
        rows=cursor.fetchmany(501)
        if len(rows)>500:
            raise ValueError('query returned too many rows')
        output=[json.dumps(list(row), ensure_ascii=False, separators=(',',':')) for row in rows]
        return FixtureResult(data['label'],columns,sorted(output))
    finally:
        connection.close()

def _safe_sql(sql):
    if not 0<len(sql)<=3000 or not re.match(r'^\s*SELECT\b',sql,re.I):
        raise ValueError('query must be a single SELECT statement of at most 3000 characters')
    if ';' in sql or '--' in sql or '/*' in sql or '*/' in sql:
        raise ValueError('comments and semicolons are not supported')
    return sql

def read_dataset(given:CaseInput,workspace:Path)->ReadOutput:
    scenario,_=_case(given.case,given.seed)
    return ReadOutput(given.case,given.seed,SCHEMA,scenario['requirement'],scenario['broken_query'],RULES)

def pin_reference(given:CaseInput,workspace:Path)->ReferenceOutput:
    scenario,raw=_case(given.case,given.seed)
    expected=[_query_fixture(data,scenario['solution']) for data in raw]
    return ReferenceOutput(given.case,given.seed,[_fixture_models(data) for data in raw],expected)

def save_candidate(given:RunInput,workspace:Path)->RunOutput:
    _,raw=_case(given.case,given.seed)
    _safe_sql(given.sql)
    results=[_query_fixture(data,given.sql) for data in raw]
    path,digest=store(workspace,{'case':given.case,'seed':given.seed,'sql':given.sql,
                                 'results':[asdict(row) for row in results]})
    return RunOutput(given.case,given.seed,given.sql,path,digest,results)
