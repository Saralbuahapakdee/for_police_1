import sqlite3
c=sqlite3.connect('users.db')
c.execute("UPDATE cameras SET mqtt_topic='cam1/' WHERE id=1")
c.execute("UPDATE cameras SET mqtt_topic='cam2/' WHERE id=2")
c.commit()
print("Updated database")
