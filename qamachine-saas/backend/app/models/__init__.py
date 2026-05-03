# Import all models so SQLAlchemy registers them with Base.metadata before create_all()
from app.models.user import User  # noqa: F401
from app.models.chat import Chat, Message  # noqa: F401
from app.models.run import Run, Subscription  # noqa: F401
from app.models.analytics import PageView, Payment  # noqa: F401
