from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import settings

client: AsyncIOMotorClient = None
database: AsyncIOMotorDatabase = None


async def connect_db():
    global client, database
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    database = client[settings.DATABASE_NAME]
    await database.users.create_index("email", unique=True)
    await database.users.create_index("role")
    await database.users.create_index("created_at")
    await database.users.create_index("reset_token")

    # CodeSprint indexes
    await database.codesprint_sessions.create_index("user_id")
    await database.codesprint_sessions.create_index("language")
    await database.codesprint_sessions.create_index("difficulty")
    await database.codesprint_sessions.create_index("wpm")
    await database.codesprint_sessions.create_index([("language", 1), ("wpm", -1)])
    await database.codesprint_sessions.create_index([("user_id", 1), ("created_at", -1)])
    await database.codesprint_sessions.create_index([("user_id", 1), ("language", 1)])
    await database.codesprint_sessions.create_index([("user_id", 1), ("difficulty", 1)])
    await database.codesprint_sessions.create_index([("user_id", 1), ("category", 1)])
    await database.codesprint_sessions.create_index([("user_id", 1), ("finished", 1)])
    await database.codesprint_sessions.create_index([("created_at", -1)])

    await database.codesprint_snippets.create_index("language")
    await database.codesprint_snippets.create_index([("language", 1), ("difficulty", 1)])

    # User stats index
    await database.codesprint_user_stats.create_index("user_id", unique=True)
    await database.codesprint_user_stats.create_index("current_streak")

    # Daily challenges indexes
    await database.codesprint_daily_challenges.create_index("date", unique=True)
    await database.codesprint_daily_challenges.create_index("created_at")

    # Gamification indexes
    await database.codesprint_achievements.create_index("key", unique=True)
    await database.codesprint_achievements.create_index("category")

    await database.codesprint_user_achievements.create_index([("user_id", 1), ("achievement_key", 1)], unique=True)
    await database.codesprint_user_achievements.create_index([("user_id", 1), ("unlocked_at", -1)])

    await database.codesprint_weekly_challenges.create_index("week_start")
    await database.codesprint_weekly_challenges.create_index([("week_start", 1), ("type", 1)])

    await database.codesprint_user_challenges.create_index([("user_id", 1), ("challenge_id", 1)], unique=True)
    await database.codesprint_user_challenges.create_index([("user_id", 1), ("completed", 1)])

    await database.codesprint_xp_history.create_index([("user_id", 1), ("created_at", -1)])
    await database.codesprint_xp_history.create_index([("user_id", 1), ("type", 1)])

    await database.codesprint_user_xp.create_index("user_id", unique=True)
    await database.codesprint_user_xp.create_index([("xp", -1)])

    await database.codesprint_rank_history.create_index([("user_id", 1), ("metric", 1)], unique=True)
    await database.codesprint_rank_history.create_index("updated_at")

    # Admin indexes
    await database.admin_logs.create_index("admin_id")
    await database.admin_logs.create_index("action")
    await database.admin_logs.create_index("resource_type")
    await database.admin_logs.create_index("created_at")
    await database.admin_logs.create_index([("admin_id", 1), ("created_at", -1)])

    await database.system_settings.create_index("key", unique=True)
    await database.system_settings.create_index("category")

    await database.snippet_categories.create_index("slug", unique=True)
    await database.snippet_categories.create_index("language")
    await database.snippet_categories.create_index("difficulty")

    await database.certificates.create_index("user_id")
    await database.certificates.create_index("verification_code", unique=True)
    await database.certificates.create_index("revoked")
    await database.certificates.create_index("created_at")

    await database.certificate_templates.create_index("name")

    await database.admin_notifications.create_index("type")
    await database.admin_notifications.create_index("created_at")
    await database.admin_notifications.create_index("is_active")

    print(f"Connected to MongoDB: {settings.DATABASE_NAME}")


async def close_db():
    global client
    if client:
        client.close()
        print("MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    return database
