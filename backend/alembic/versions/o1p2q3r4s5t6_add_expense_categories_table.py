"""Add expense_categories table and seed system categories

Revision ID: o1p2q3r4s5t6
Revises: n0o1p2q3r4s5
Create Date: 2026-02-22
"""
from alembic import op
import sqlalchemy as sa

revision = 'o1p2q3r4s5t6'
down_revision = 'n0o1p2q3r4s5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE IF NOT EXISTS expense_categories (
            id SERIAL PRIMARY KEY,
            user_id INTEGER REFERENCES users(id),
            name VARCHAR NOT NULL,
            description TEXT,
            icon VARCHAR,
            color VARCHAR,
            parent_id INTEGER REFERENCES expense_categories(id),
            is_system BOOLEAN NOT NULL DEFAULT FALSE,
            is_income BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            keywords TEXT,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            updated_at TIMESTAMPTZ
        );
        CREATE INDEX IF NOT EXISTS ix_expense_categories_name ON expense_categories (name);
        -- Unique partial index: system category names must be unique
        CREATE UNIQUE INDEX IF NOT EXISTS uq_expense_categories_system_name
            ON expense_categories (name) WHERE is_system = true AND user_id IS NULL;
    """)

    # Seed 20 default system expense categories with keywords for auto-categorization
    op.execute("""
        INSERT INTO expense_categories (user_id, name, description, icon, color, is_system, is_income, is_active, keywords) VALUES
            (NULL, 'Groceries',            'Food and household items',                '🛒', '#4CAF50', true, false, true,
             'grocery,supermarket,walmart,target,costco,whole foods,trader joe,safeway,kroger,food,vegetables,fruits,meat,dairy'),
            (NULL, 'Dining & Restaurants',  'Eating out, restaurants, cafes',          '🍽️', '#FF9800', true, false, true,
             'restaurant,cafe,coffee,starbucks,mcdonald,burger,pizza,food delivery,uber eats,doordash,grubhub,zomato,swiggy,dining,eatery'),
            (NULL, 'Transportation',        'Fuel, public transport, ride-sharing',    '🚗', '#2196F3', true, false, true,
             'uber,lyft,taxi,cab,fuel,gas,petrol,diesel,metro,bus,train,parking,toll,transport,ola'),
            (NULL, 'Utilities',             'Electricity, water, gas, internet',       '💡', '#FFC107', true, false, true,
             'electricity,water,gas,internet,broadband,wifi,phone bill,mobile,utility,power,energy'),
            (NULL, 'Rent & Mortgage',       'Housing payments',                        '🏠', '#9C27B0', true, false, true,
             'rent,mortgage,housing,lease,landlord,property,apartment'),
            (NULL, 'Healthcare & Medical',  'Doctor visits, medicines, insurance',     '⚕️', '#F44336', true, false, true,
             'doctor,hospital,clinic,pharmacy,medicine,medical,health,insurance,dental,prescription,lab test'),
            (NULL, 'Entertainment',         'Movies, games, hobbies',                  '🎬', '#E91E63', true, false, true,
             'movie,cinema,netflix,spotify,amazon prime,disney,gaming,xbox,playstation,entertainment,concert,theater'),
            (NULL, 'Shopping & Clothing',   'Clothes, accessories, personal items',    '👕', '#673AB7', true, false, true,
             'clothing,clothes,fashion,shoes,accessories,mall,amazon,flipkart,myntra,shopping,apparel'),
            (NULL, 'Education',             'Tuition, books, courses',                 '📚', '#3F51B5', true, false, true,
             'school,college,university,tuition,books,course,education,training,udemy,coursera,learning'),
            (NULL, 'Fitness & Gym',         'Gym membership, sports, fitness',         '💪', '#FF5722', true, false, true,
             'gym,fitness,yoga,sports,workout,exercise,trainer,membership,health club'),
            (NULL, 'Travel & Vacation',     'Hotels, flights, vacation expenses',      '✈️', '#00BCD4', true, false, true,
             'hotel,flight,airline,booking,airbnb,travel,vacation,trip,tourism,resort'),
            (NULL, 'Insurance',             'Life, health, car insurance',             '🛡️', '#607D8B', true, false, true,
             'insurance,premium,policy,life insurance,health insurance,car insurance'),
            (NULL, 'Personal Care',         'Salon, spa, grooming',                    '💇', '#E91E63', true, false, true,
             'salon,spa,haircut,beauty,grooming,cosmetics,skincare,barber'),
            (NULL, 'Subscriptions',         'Monthly subscriptions and memberships',   '📱', '#9E9E9E', true, false, true,
             'subscription,membership,monthly,recurring,netflix,spotify,amazon prime,youtube premium'),
            (NULL, 'Gifts & Donations',     'Gifts, charity, donations',              '🎁', '#FF4081', true, false, true,
             'gift,donation,charity,present,contribution,ngo'),
            (NULL, 'Pet Care',              'Pet food, vet, supplies',                 '🐾', '#795548', true, false, true,
             'pet,dog,cat,vet,veterinary,pet food,pet supplies,grooming'),
            (NULL, 'Home Maintenance',      'Repairs, cleaning, maintenance',          '🔧', '#607D8B', true, false, true,
             'repair,maintenance,plumber,electrician,cleaning,handyman,home improvement'),
            (NULL, 'Taxes',                 'Income tax, property tax',                '📋', '#455A64', true, false, true,
             'tax,income tax,property tax,tds,gst,irs'),
            (NULL, 'Salary & Income',       'Salary, wages, income',                   '💰', '#4CAF50', true, true,  true,
             'salary,wage,income,payment,paycheck,earnings,compensation'),
            (NULL, 'Investments & Returns', 'Investment returns, dividends, interest', '📈', '#009688', true, true,  true,
             'dividend,interest,investment,returns,profit,capital gain,mutual fund')
        ON CONFLICT (name) WHERE is_system = true AND user_id IS NULL DO NOTHING;
    """)


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS expense_categories;")
