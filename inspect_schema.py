import psycopg2
cfg = {
    'host': 'localhost',
    'database': 'data_lab',
    'user': 'postgres',
    'password': '12345'
}
conn = psycopg2.connect(**cfg)
with conn.cursor() as cur:
    cur.execute("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema='warehouse' ORDER BY table_name")
    print('TABLES:')
    for row in cur.fetchall():
        print(row)
    cur.execute("SELECT column_name, data_type FROM information_schema.columns WHERE table_schema='warehouse' AND table_name='fait_ventes' ORDER BY ordinal_position")
    print('COLUMNS:')
    for row in cur.fetchall():
        print(row)
conn.close()
