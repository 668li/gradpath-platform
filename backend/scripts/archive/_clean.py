import psycopg2
conn=psycopg2.connect('postgresql://gradpath:changeme@db:5432/gradpath')
cur=conn.cursor()
cur.execute("DELETE FROM feedback WHERE session_id IN ('widget-test','test-sess-001')")
cur.execute("DELETE FROM events WHERE session_id='test-sess-001'")
conn.commit()
print('cleaned')
cur.close(); conn.close()
