from app.core.database import engine
from sqlalchemy import text

with engine.connect() as conn:
    result = conn.execute(text("SELECT typname FROM pg_type WHERE typname = 'cryptoexchange'"))
    exists = result.fetchone() is not None
    print(f'cryptoexchange enum exists: {exists}')
    
    if exists:
        print('Dropping existing enum...')
        conn.execute(text("DROP TYPE IF EXISTS cryptoexchange CASCADE"))
        conn.commit()
        print('Enum dropped successfully')

# Made with Bob
