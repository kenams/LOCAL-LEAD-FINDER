#!/usr/bin/env python3
"""
Seed database with sample data
"""
from app.db.session import SessionLocal, init_db
from app.models.prospect import Prospect
from faker import Faker
import random

fake = Faker('fr_FR')

def seed_database():
    """Add sample prospects for testing"""
    init_db()

    db = SessionLocal()

    try:
        # Clear existing
        db.query(Prospect).delete()

        # Sample prospects
        prospects_data = [
            {
                "business_name": "Coiffure Elegance",
                "category": "coiffeur",
                "location": "Toulouse",
                "website": "https://coiffure-elegance-toulouse.fr",
                "email": "contact@coiffure-elegance-toulouse.fr",
                "phone": "05 61 23 45 67",
                "opportunity_score": 75.0,
                "site_quality_score": 45.0,
                "feasibility": "MEDIUM",
                "estimated_time": "3 à 5 jours",
                "estimated_price_min": 700.0,
                "estimated_price_max": 1000.0,
                "detected_issues": "no_responsive,no_cta,old_design",
                "status": "NEW"
            },
            {
                "business_name": "Institut Beauté Zen",
                "category": "institut de beauté",
                "location": "Montpellier",
                "website": "https://beautzen-montpellier.com",
                "email": "info@beautzen-montpellier.com",
                "phone": "04 67 12 34 56",
                "opportunity_score": 82.0,
                "site_quality_score": 38.0,
                "feasibility": "EASY",
                "estimated_time": "1 à 2 jours",
                "estimated_price_min": 400.0,
                "estimated_price_max": 600.0,
                "detected_issues": "no_https,no_booking",
                "status": "REVIEWED"
            },
            {
                "business_name": "Plomberie Express",
                "category": "plombier",
                "location": "Marseille",
                "website": "https://plomberie-express-marseille.fr",
                "phone": "04 91 23 45 67",
                "opportunity_score": 68.0,
                "site_quality_score": 52.0,
                "feasibility": "ADVANCED",
                "estimated_time": "5 à 10 jours",
                "estimated_price_min": 1200.0,
                "estimated_price_max": 2000.0,
                "detected_issues": "no_services,no_testimonials",
                "status": "NEW"
            }
        ]

        for data in prospects_data:
            prospect = Prospect(**data)
            db.add(prospect)

        # Generate some fake prospects
        categories = ["coiffeur", "restaurant", "plombier", "dentiste", "avocat"]
        locations = ["Toulouse", "Montpellier", "Marseille", "Paris"]

        for _ in range(10):
            category = random.choice(categories)
            location = random.choice(locations)

            prospect = Prospect(
                business_name=fake.company(),
                category=category,
                location=location,
                website=fake.url(),
                email=fake.email(),
                phone=fake.phone_number(),
                opportunity_score=random.randint(50, 90),
                site_quality_score=random.randint(30, 70),
                feasibility=random.choice(["EASY", "MEDIUM", "ADVANCED"]),
                estimated_time=random.choice(["1 à 2 jours", "3 à 5 jours", "5 à 10 jours"]),
                estimated_price_min=random.choice([400, 700, 1200]),
                estimated_price_max=random.choice([600, 1000, 2000]),
                status=random.choice(["NEW", "REVIEWED", "CONTACTED"]),
                source="sample_data"
            )
            db.add(prospect)

        db.commit()
        print("Sample data added successfully")

    except Exception as e:
        db.rollback()
        print(f"Error seeding database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()