"""Model registry.

Importing this package loads every model module, ensuring Base.metadata has
the complete schema regardless of which entry point (endpoint, script, agent,
scheduler) triggered the import.
"""

from app.models import construction  # noqa: F401
from app.models import ai_layer  # noqa: F401