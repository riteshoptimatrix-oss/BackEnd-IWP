import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from motor.motor_asyncio import AsyncIOMotorClient
from passlib.context import CryptContext
from datetime import datetime

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

MONGODB_URL = "mongodb://localhost:27017"
DATABASE_NAME = "indiawebprogrammers"

ADMIN_EMAIL = "ritesh.work.1510@gmail.com"
ADMIN_PASSWORD = "8980614160@.com"
ADMIN_NAME = "Ritesh Admin"


async def seed():
    client = AsyncIOMotorClient(MONGODB_URL)
    db = client[DATABASE_NAME]

    print("Connected to MongoDB...")

    existing = await db.users.find_one({"email": ADMIN_EMAIL})
    if existing:
        print(f"Admin user '{ADMIN_EMAIL}' already exists with role: {existing.get('role')}")
        if existing.get("role") != "super_admin":
            await db.users.update_one(
                {"email": ADMIN_EMAIL},
                {"$set": {"role": "super_admin", "updated_at": datetime.utcnow()}}
            )
            print("Updated role to super_admin")
    else:
        user_data = {
            "full_name": ADMIN_NAME,
            "email": ADMIN_EMAIL,
            "password_hash": pwd_context.hash(ADMIN_PASSWORD),
            "avatar": None,
            "phone": None,
            "role": "super_admin",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "last_login": None,
            "email_verified": True,
            "two_factor_enabled": False,
            "account_status": "active",
            "theme_preference": "dark",
            "notification_settings": {
                "email_notifications": True,
                "project_updates": True,
                "ai_reports": True,
                "security_alerts": True,
                "marketing": False,
            },
            "timezone": "UTC",
            "language": "en",
            "reset_token": None,
            "reset_token_expires": None,
            "verification_token": None,
            "company": "India Web Programmers",
            "bio": "Super Admin of CodeSprint Enterprise Panel",
            "social_links": {"twitter": "", "linkedin": "", "github": "", "website": ""},
        }
        result = await db.users.insert_one(user_data)
        print(f"Created admin user: {ADMIN_EMAIL} (ID: {result.inserted_id})")

    default_settings = [
        {
            "key": "languages",
            "value": {
                "supported": ["html", "css", "javascript", "react", "nextjs", "typescript", "dart", "angular", "vue"],
                "enabled": ["html", "css", "javascript", "react", "nextjs", "typescript", "dart", "angular", "vue"],
            },
            "category": "languages",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "key": "difficulty_levels",
            "value": {
                "levels": ["beginner", "intermediate", "advanced", "expert"],
                "defaults": {"beginner": 60, "intermediate": 120, "advanced": 180, "expert": 300},
            },
            "category": "difficulty",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "key": "challenge_duration",
            "value": {
                "daily_seconds": 180,
                "weekly_seconds": 600,
                "min_seconds": 30,
                "max_seconds": 1800,
            },
            "category": "challenges",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "key": "xp_rules",
            "value": {
                "session_complete": 10,
                "daily_challenge": 50,
                "weekly_challenge": 200,
                "streak_bonus_per_day": 5,
                "perfect_accuracy_bonus": 25,
                "daily_login": 10,
                "first_session_of_day": 15,
            },
            "category": "gamification",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "key": "level_rules",
            "value": {
                "levels": [
                    {"level": 1, "xp_required": 0, "title": "Beginner"},
                    {"level": 2, "xp_required": 100, "title": "Novice"},
                    {"level": 3, "xp_required": 300, "title": "Apprentice"},
                    {"level": 4, "xp_required": 600, "title": "Practitioner"},
                    {"level": 5, "xp_required": 1000, "title": "Expert"},
                    {"level": 6, "xp_required": 1500, "title": "Master"},
                    {"level": 7, "xp_required": 2200, "title": "Grandmaster"},
                    {"level": 8, "xp_required": 3000, "title": "Champion"},
                    {"level": 9, "xp_required": 4000, "title": "Legend"},
                    {"level": 10, "xp_required": 5500, "title": "Mythic"},
                ],
            },
            "category": "gamification",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
        {
            "key": "achievement_rules",
            "value": {
                "bronze_xp": 25,
                "silver_xp": 50,
                "gold_xp": 100,
                "max_daily_achievements": 5,
            },
            "category": "gamification",
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
        },
    ]

    for setting in default_settings:
        existing_setting = await db.system_settings.find_one({"key": setting["key"]})
        if not existing_setting:
            await db.system_settings.insert_one(setting)
            print(f"Created setting: {setting['key']}")
        else:
            print(f"Setting '{setting['key']}' already exists, skipping")

    default_categories = [
        {"name": "Basic Markup", "slug": "basic-markup", "description": "Simple HTML structures", "language": "html", "difficulty": "beginner", "sort_order": 1},
        {"name": "Semantic HTML", "slug": "semantic-html", "description": "HTML5 semantic elements", "language": "html", "difficulty": "intermediate", "sort_order": 2},
        {"name": "Forms & Validation", "slug": "forms-validation", "description": "HTML forms and input handling", "language": "html", "difficulty": "intermediate", "sort_order": 3},
        {"name": "Layout Basics", "slug": "layout-basics", "description": "Flexbox and Grid fundamentals", "language": "css", "difficulty": "beginner", "sort_order": 1},
        {"name": "Animations", "slug": "animations", "description": "CSS transitions and animations", "language": "css", "difficulty": "intermediate", "sort_order": 2},
        {"name": "Responsive Design", "slug": "responsive-design", "description": "Media queries and responsive layouts", "language": "css", "difficulty": "intermediate", "sort_order": 3},
        {"name": "Variables & Functions", "slug": "variables-functions", "description": "JavaScript variables, functions, scopes", "language": "javascript", "difficulty": "beginner", "sort_order": 1},
        {"name": "Async Patterns", "slug": "async-patterns", "description": "Promises, async/await, callbacks", "language": "javascript", "difficulty": "intermediate", "sort_order": 2},
        {"name": "DOM Manipulation", "slug": "dom-manipulation", "description": "Document Object Model operations", "language": "javascript", "difficulty": "intermediate", "sort_order": 3},
        {"name": "Components & JSX", "slug": "components-jsx", "description": "React component patterns", "language": "react", "difficulty": "beginner", "sort_order": 1},
        {"name": "Hooks", "slug": "hooks", "description": "useState, useEffect, custom hooks", "language": "react", "difficulty": "intermediate", "sort_order": 2},
        {"name": "State Management", "slug": "state-management", "description": "Context API, useReducer, external stores", "language": "react", "difficulty": "advanced", "sort_order": 3},
        {"name": "App Router", "slug": "app-router", "description": "Next.js App Router patterns", "language": "nextjs", "difficulty": "beginner", "sort_order": 1},
        {"name": "Server Components", "slug": "server-components", "description": "RSC and server-side rendering", "language": "nextjs", "difficulty": "intermediate", "sort_order": 2},
        {"name": "API Routes", "slug": "api-routes", "description": "Next.js API route handlers", "language": "nextjs", "difficulty": "intermediate", "sort_order": 3},
        {"name": "Type Basics", "slug": "type-basics", "description": "Types, interfaces, enums", "language": "typescript", "difficulty": "beginner", "sort_order": 1},
        {"name": "Generics", "slug": "generics", "description": "Generic types and constraints", "language": "typescript", "difficulty": "intermediate", "sort_order": 2},
        {"name": "Utility Types", "slug": "utility-types", "description": "Partial, Pick, Omit, Record, etc.", "language": "typescript", "difficulty": "advanced", "sort_order": 3},
        {"name": "Dart Fundamentals", "slug": "dart-fundamentals", "description": "Dart language basics", "language": "dart", "difficulty": "beginner", "sort_order": 1},
        {"name": "Null Safety", "slug": "null-safety", "description": "Dart null safety patterns", "language": "dart", "difficulty": "intermediate", "sort_order": 2},
        {"name": "Component Basics", "slug": "angular-component-basics", "description": "Angular component patterns", "language": "angular", "difficulty": "beginner", "sort_order": 1},
        {"name": "Services & DI", "slug": "services-di", "description": "Angular services and dependency injection", "language": "angular", "difficulty": "intermediate", "sort_order": 2},
        {"name": "Composition API", "slug": "composition-api", "description": "Vue 3 Composition API patterns", "language": "vue", "difficulty": "beginner", "sort_order": 1},
        {"name": "Reactivity", "slug": "reactivity", "description": "Vue reactivity system and refs", "language": "vue", "difficulty": "intermediate", "sort_order": 2},
    ]

    for cat in default_categories:
        existing_cat = await db.snippet_categories.find_one({"slug": cat["slug"]})
        if not existing_cat:
            cat["created_at"] = datetime.utcnow()
            cat["updated_at"] = datetime.utcnow()
            cat["icon"] = None
            cat["snippet_count"] = 0
            await db.snippet_categories.insert_one(cat)
            print(f"Created category: {cat['name']}")
        else:
            print(f"Category '{cat['name']}' already exists, skipping")

    print("\nSeed completed successfully!")
    print(f"\nAdmin Login Credentials:")
    print(f"  Email:    {ADMIN_EMAIL}")
    print(f"  Password: {ADMIN_PASSWORD}")
    print(f"  Role:     super_admin")

    client.close()


if __name__ == "__main__":
    asyncio.run(seed())
