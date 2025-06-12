"""
global context vars definition

Used to store context variables shared between plugins and the core system.
Solves circular dependency problems by injecting into __builtins__.
"""

import threading
from contextvars import ContextVar

# define context vars
tracer_context: ContextVar[str] = ContextVar(
    "tracer_context", default="default_trace_id"
)
tenant_context: ContextVar[str] = ContextVar("tenant_context", default="default_tenant")

# thread local storage as a fallback
_thread_local = threading.local()


def set_thread_trace_id(trace_id: str):
    """set thread local trace_id"""
    _thread_local.trace_id = trace_id


def get_thread_trace_id() -> str:
    """get thread local trace_id"""
    return getattr(_thread_local, "trace_id", "default_trace_id")


def set_thread_tenant_id(tenant_id: str):
    """set thread local tenant_id"""
    _thread_local.tenant_id = tenant_id


def get_thread_tenant_id() -> str:
    """get thread local tenant_id"""
    return getattr(_thread_local, "tenant_id", "default_tenant")


def inject_global_vars():
    """
    Inject global context variables into __builtins__

    This is done to solve the circular dependency problem between plugins and the core system:
    - Plugin code cannot directly import system modules
    - Sharing variables through __builtins__ can avoid circular imports
    """
    if isinstance(__builtins__, dict):
        __builtins__["tracer_context"] = tracer_context
        __builtins__["tenant_context"] = tenant_context
        __builtins__["set_thread_trace_id"] = set_thread_trace_id
        __builtins__["get_thread_trace_id"] = get_thread_trace_id
        __builtins__["set_thread_tenant_id"] = set_thread_tenant_id
        __builtins__["get_thread_tenant_id"] = get_thread_tenant_id
    else:
        setattr(__builtins__, "tracer_context", tracer_context)
        setattr(__builtins__, "tenant_context", tenant_context)
        setattr(__builtins__, "set_thread_trace_id", set_thread_trace_id)
        setattr(__builtins__, "get_thread_trace_id", get_thread_trace_id)
        setattr(__builtins__, "set_thread_tenant_id", set_thread_tenant_id)
        setattr(__builtins__, "get_thread_tenant_id", get_thread_tenant_id)


# export all context variables for other modules to import
__all__ = [
    "tracer_context",
    "tenant_context",
    "inject_global_vars",
    "set_thread_trace_id",
    "get_thread_trace_id",
    "set_thread_tenant_id",
    "get_thread_tenant_id",
]
