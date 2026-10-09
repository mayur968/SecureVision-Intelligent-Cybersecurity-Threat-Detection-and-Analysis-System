import sqlite3, sys
sys.path.insert(0, '.')

con = sqlite3.connect('securevision.db')
con.row_factory = sqlite3.Row

row = con.execute(
    'SELECT id, scan_type, input_value, prediction, confidence, '
    'risk_level, risk_score, model_version, status, is_demo_data, '
    'duration_ms, created_at FROM scan_history ORDER BY id DESC LIMIT 1'
).fetchone()

print('=== Latest scan_history row ===')
for k in row.keys():
    print(f'  {k:<18}: {row[k]}')

scan_id = row['id']

iocs = con.execute(
    'SELECT i.ioc_type, i.value, i.seen_count FROM ioc i '
    'JOIN scan_ioc si ON i.id = si.ioc_id WHERE si.scan_id = ? '
    'ORDER BY i.ioc_type, i.value',
    (scan_id,)
).fetchall()

print(f'\n=== IOCs for scan {scan_id} ({len(iocs)} total) ===')
for ioc in iocs:
    t = ioc['ioc_type']
    v = ioc['value']
    s = ioc['seen_count']
    print(f'  [{t:<12}] {v:<50} seen_count={s}')

print('\n=== model_registry ===')
for mr in con.execute(
    'SELECT id, algorithm, dataset_name, is_synthetic_data, training_date '
    'FROM model_registry'
).fetchall():
    mid = mr['id']
    alg = mr['algorithm']
    ds  = mr['dataset_name']
    syn = mr['is_synthetic_data']
    td  = str(mr['training_date'])[:10]
    print(f'  {mid:<22} {alg:<22} synthetic={syn} trained={td}')

total_iocs = con.execute('SELECT COUNT(*) FROM ioc').fetchone()[0]
total_scans = con.execute('SELECT COUNT(*) FROM scan_history').fetchone()[0]
print(f'\n=== Totals: {total_iocs} unique IOCs across {total_scans} scans ===')
con.close()
