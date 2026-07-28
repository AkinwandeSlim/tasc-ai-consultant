"""Infrastructure adapters — providers, vector store, repositories, automation, prompts.

Sprint 4 includes a lightweight in-memory session store. The abstract
SessionRepository interface is designed so Redis can replace the backing
store without changing callers.
"""
