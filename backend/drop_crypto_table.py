from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    print('Dropping crypto_accounts table...')
    conn.execute(text("DROP TABLE IF EXISTS crypto_accounts CASCADE"))
    conn.commit()
    print('Table dropped successfully')

# Made with Bob
