import sqlite3
c=sqlite3.connect('users.db')
c.execute("UPDATE cameras SET mqtt_topic='A1G3774HC' WHERE id=1")
c.execute("UPDATE cameras SET mqtt_topic='BG774LGG3' WHERE id=2")
c.commit()
print("Updated database")
