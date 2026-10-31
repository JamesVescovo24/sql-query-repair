"""Small deterministic but seeded SQLite fixtures; no external database or API."""
SCHEMA = '''
CREATE TABLE customers (customer_id INTEGER PRIMARY KEY, region TEXT NOT NULL);
CREATE TABLE orders (order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, status TEXT NOT NULL, due_date TEXT NOT NULL);
CREATE TABLE payments (payment_id INTEGER PRIMARY KEY, order_id INTEGER NOT NULL, amount_cents INTEGER NOT NULL);
'''.strip()
CASES = {
    'region-revenue': {
        'requirement': 'Report paid revenue by customer region; include each payment once, grouped by region. Return columns region and total_cents, with total_cents in integer cents. Exclude regions with no payments.',
        'broken_query': '''SELECT c.region AS region, SUM(p.amount_cents) AS total_cents
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.customer_id
JOIN payments AS p ON p.order_id = o.customer_id
GROUP BY c.region ORDER BY c.region''',
        'solution': '''SELECT c.region AS region, SUM(p.amount_cents) AS total_cents
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.customer_id
JOIN payments AS p ON p.order_id = o.order_id
GROUP BY c.region ORDER BY c.region''',
        'columns': ['region','total_cents'],
    },
    'overdue-count': {
        'requirement': "Count OPEN orders with due_date strictly earlier than 2026-10-01, grouped by customer region. Return only regions with qualifying orders and columns region and overdue_orders.",
        'broken_query': '''SELECT c.region AS region, COUNT(*) AS overdue_orders
FROM customers AS c
LEFT JOIN orders AS o ON o.customer_id = c.customer_id AND o.due_date < '2026-10-01'
GROUP BY c.region ORDER BY c.region''',
        'solution': '''SELECT c.region AS region, COUNT(*) AS overdue_orders
FROM customers AS c
JOIN orders AS o ON o.customer_id = c.customer_id
WHERE o.status = 'OPEN' AND o.due_date < '2026-10-01'
GROUP BY c.region ORDER BY c.region''',
        'columns':['region','overdue_orders'],
    },
}
RULES = ('Write a single read-only SELECT statement. The tool executes it on three distinct deterministic SQLite '
         'fixtures and returns results; you may retry after reviewing them. A result is correct only when the '
         'columns and multiset of rows match the reference on ALL three fixtures. '
         'The verifier checks saved query and actual rows, not the agent\'s claim. No SQL mutations or multiple statements.')

def fixtures(seed):
    if type(seed) is not int or seed < 1 or seed > 10000:
        raise ValueError('seed must be an integer from 1 to 10000')
    result=[]
    for index in range(3):
        off=index*100+((seed*37)%25)*10
        customers=[{'customer_id':1,'region':'East'}, {'customer_id':2,'region':'West'},
                   {'customer_id':3,'region':'East'}, {'customer_id':4,'region':'Central'}, {'customer_id':5,'region':'West'}]
        orders=[
            {'order_id':off+1,'customer_id':1,'status':'CLOSED' if index==2 else 'OPEN','due_date':'2026-09-20'},
            {'order_id':off+2,'customer_id':2,'status':'OPEN','due_date':'2026-11-20'},
            {'order_id':off+3,'customer_id':1,'status':'CLOSED','due_date':'2026-09-10'},
            {'order_id':off+4,'customer_id':3,'status':'CLOSED' if index==2 else 'OPEN','due_date':'2026-08-15'},
            {'order_id':off+5,'customer_id':4,'status':'CLOSED' if index==2 else 'OPEN','due_date':'2026-10-15' if index==1 else '2026-09-01'},
            {'order_id':off+6,'customer_id':5,'status':'OPEN','due_date':'2026-11-01' if index==2 else '2026-09-14'},
        ]
        n=((seed * (index+3))%71)*7
        pays=[
            {'payment_id':1,'order_id':off+1,'amount_cents':1000+n},
            {'payment_id':2,'order_id':off+1,'amount_cents':500+index*15},
            {'payment_id':3,'order_id':off+2,'amount_cents':750+n},
            {'payment_id':4,'order_id':off+3,'amount_cents':90+index*20},
            {'payment_id':5,'order_id':off+4,'amount_cents':800+n},
            {'payment_id':6,'order_id':off+6,'amount_cents':250+index*10},
        ]
        result.append({'label':f'fixture-{index+1}','customers':customers,'orders':orders,'payments':pays})
    return result
