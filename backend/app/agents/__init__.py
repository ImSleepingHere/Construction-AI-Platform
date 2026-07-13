"""Agent framework package.

Importing this module triggers registration of all built-in tools by
importing the tool modules that use @tool.
"""

# Import tool modules for their decorator side effects.
from app.agents import memory  # noqa: F401