import sqlite3

conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Create users table
cursor.execute('''
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL
)
''')

# Insert default admin
cursor.execute('''
INSERT OR IGNORE INTO users (email, password, role)
VALUES (?, ?, ?)
''', ('vardan.kumar@innovasolutions.com', 'admin123', 'admin'))

# Insert default customer
cursor.execute('''
INSERT OR IGNORE INTO users (email, password, role)
VALUES (?, ?, ?)
''', ('customer@example.com', 'user123', 'customer'))

conn.commit()
conn.close()

print("✅ users table created and sample data inserted.")
