"""
Seed script to populate default expense categories with keywords
Run this script to add 20 common expense categories to the database
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy.orm import Session
from app.core.database import SessionLocal, engine
from app.models.expense_category import ExpenseCategory

# 20 Common expense categories with associated keywords
DEFAULT_CATEGORIES = [
    {
        "name": "Groceries",
        "description": "Food and household items",
        "icon": "🛒",
        "color": "#4CAF50",
        "is_income": False,
        "keywords": "grocery,supermarket,walmart,target,costco,whole foods,trader joe,safeway,kroger,food,vegetables,fruits,meat,dairy"
    },
    {
        "name": "Dining & Restaurants",
        "description": "Eating out, restaurants, cafes",
        "icon": "🍽️",
        "color": "#FF9800",
        "is_income": False,
        "keywords": "restaurant,cafe,coffee,starbucks,mcdonald,burger,pizza,food delivery,uber eats,doordash,grubhub,zomato,swiggy,dining,eatery"
    },
    {
        "name": "Transportation",
        "description": "Fuel, public transport, ride-sharing",
        "icon": "🚗",
        "color": "#2196F3",
        "is_income": False,
        "keywords": "uber,lyft,taxi,cab,fuel,gas,petrol,diesel,metro,bus,train,parking,toll,transport,ola"
    },
    {
        "name": "Utilities",
        "description": "Electricity, water, gas, internet",
        "icon": "💡",
        "color": "#FFC107",
        "is_income": False,
        "keywords": "electricity,water,gas,internet,broadband,wifi,phone bill,mobile,utility,power,energy"
    },
    {
        "name": "Rent & Mortgage",
        "description": "Housing payments",
        "icon": "🏠",
        "color": "#9C27B0",
        "is_income": False,
        "keywords": "rent,mortgage,housing,lease,landlord,property,apartment"
    },
    {
        "name": "Healthcare & Medical",
        "description": "Doctor visits, medicines, insurance",
        "icon": "⚕️",
        "color": "#F44336",
        "is_income": False,
        "keywords": "doctor,hospital,clinic,pharmacy,medicine,medical,health,insurance,dental,prescription,lab test"
    },
    {
        "name": "Entertainment",
        "description": "Movies, games, hobbies",
        "icon": "🎬",
        "color": "#E91E63",
        "is_income": False,
        "keywords": "movie,cinema,netflix,spotify,amazon prime,disney,gaming,xbox,playstation,entertainment,concert,theater"
    },
    {
        "name": "Shopping & Clothing",
        "description": "Clothes, accessories, personal items",
        "icon": "👕",
        "color": "#673AB7",
        "is_income": False,
        "keywords": "clothing,clothes,fashion,shoes,accessories,mall,amazon,flipkart,myntra,shopping,apparel"
    },
    {
        "name": "Education",
        "description": "Tuition, books, courses",
        "icon": "📚",
        "color": "#3F51B5",
        "is_income": False,
        "keywords": "school,college,university,tuition,books,course,education,training,udemy,coursera,learning"
    },
    {
        "name": "Fitness & Gym",
        "description": "Gym membership, sports, fitness",
        "icon": "💪",
        "color": "#FF5722",
        "is_income": False,
        "keywords": "gym,fitness,yoga,sports,workout,exercise,trainer,membership,health club"
    },
    {
        "name": "Travel & Vacation",
        "description": "Hotels, flights, vacation expenses",
        "icon": "✈️",
        "color": "#00BCD4",
        "is_income": False,
        "keywords": "hotel,flight,airline,booking,airbnb,travel,vacation,trip,tourism,resort"
    },
    {
        "name": "Insurance",
        "description": "Life, health, car insurance",
        "icon": "🛡️",
        "color": "#607D8B",
        "is_income": False,
        "keywords": "insurance,premium,policy,life insurance,health insurance,car insurance"
    },
    {
        "name": "Personal Care",
        "description": "Salon, spa, grooming",
        "icon": "💇",
        "color": "#E91E63",
        "is_income": False,
        "keywords": "salon,spa,haircut,beauty,grooming,cosmetics,skincare,barber"
    },
    {
        "name": "Subscriptions",
        "description": "Monthly subscriptions and memberships",
        "icon": "📱",
        "color": "#9E9E9E",
        "is_income": False,
        "keywords": "subscription,membership,monthly,recurring,netflix,spotify,amazon prime,youtube premium"
    },
    {
        "name": "Gifts & Donations",
        "description": "Gifts, charity, donations",
        "icon": "🎁",
        "color": "#FF4081",
        "is_income": False,
        "keywords": "gift,donation,charity,present,contribution,ngo"
    },
    {
        "name": "Pet Care",
        "description": "Pet food, vet, supplies",
        "icon": "🐾",
        "color": "#795548",
        "is_income": False,
        "keywords": "pet,dog,cat,vet,veterinary,pet food,pet supplies,grooming"
    },
    {
        "name": "Home Maintenance",
        "description": "Repairs, cleaning, maintenance",
        "icon": "🔧",
        "color": "#607D8B",
        "is_income": False,
        "keywords": "repair,maintenance,plumber,electrician,cleaning,handyman,home improvement"
    },
    {
        "name": "Taxes",
        "description": "Income tax, property tax",
        "icon": "📋",
        "color": "#455A64",
        "is_income": False,
        "keywords": "tax,income tax,property tax,tds,gst,irs"
    },
    {
        "name": "Salary & Income",
        "description": "Salary, wages, income",
        "icon": "💰",
        "color": "#4CAF50",
        "is_income": True,
        "keywords": "salary,wage,income,payment,paycheck,earnings,compensation"
    },
    {
        "name": "Investments & Returns",
        "description": "Investment returns, dividends, interest",
        "icon": "📈",
        "color": "#009688",
        "is_income": True,
        "keywords": "dividend,interest,investment,returns,profit,capital gain,mutual fund"
    }
]


def seed_categories():
    """Seed default expense categories"""
    db = SessionLocal()
    
    try:
        # Check if categories already exist
        existing_count = db.query(ExpenseCategory).filter(
            ExpenseCategory.is_system == True
        ).count()
        
        if existing_count > 0:
            print(f"Found {existing_count} existing system categories. Skipping seed.")
            return
        
        print("Seeding default expense categories...")
        
        for cat_data in DEFAULT_CATEGORIES:
            category = ExpenseCategory(
                **cat_data,
                is_system=True,
                is_active=True,
                user_id=None  # System categories don't belong to any user
            )
            db.add(category)
        
        db.commit()
        print(f"✅ Successfully seeded {len(DEFAULT_CATEGORIES)} expense categories!")
        
        # Print summary
        print("\nCategories added:")
        for cat in DEFAULT_CATEGORIES:
            print(f"  {cat['icon']} {cat['name']} - {len(cat['keywords'].split(','))} keywords")
    
    except Exception as e:
        print(f"❌ Error seeding categories: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    print("=" * 60)
    print("Expense Category Seeder")
    print("=" * 60)
    seed_categories()
    print("=" * 60)

# Made with Bob
