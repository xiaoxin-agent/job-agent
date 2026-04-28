"""Site adapter registry for job content extraction.

Each adapter is a module in sites/ with an extract(html, url) function
that returns a dict {title, company, location, description, job_type}.
"""

from typing import Dict, Optional, Callable, List
import re
import importlib
import logging

logger = logging.getLogger(__name__)

# Adapter registry: mapping of URL patterns to (module_name, priority)
# priority: higher = checked first (for overlapping patterns)
_ADAPTERS: List[tuple] = []  # (pattern_fn, module_name, priority)
_REGISTERED = False


def register(pattern: str, module_name: str, priority: int = 0) -> None:
    """Register a URL pattern to a site adapter module."""
    def pattern_fn(url: str) -> bool:
        return pattern in url.lower()
    _ADAPTERS.append((pattern_fn, module_name, priority))


def register_fn(pattern_fn, module_name: str, priority: int = 0) -> None:
    """Register a custom function-based matcher."""
    _ADAPTERS.append((pattern_fn, module_name, priority))


def _ensure_registered():
    """Register built-in site adapters (idempotent)."""
    global _REGISTERED
    if _REGISTERED:
        return
    _REGISTERED = True

    # Google Careers
    register('google.com/about/careers', 'sites.google_careers', priority=10)
    register('careers.google.com', 'sites.google_careers', priority=10)

    # Amazon jobs
    register('amazon.jobs', 'sites.amazon', priority=10)
    register('amazon.com/jobs', 'sites.amazon', priority=10)

    # LinkedIn
    register('linkedin.com/jobs', 'sites.linkedin', priority=10)

    # Indeed
    register('indeed.com', 'sites.indeed', priority=5)

    # Canonical / Ubuntu
    register('canonical.com/careers', 'sites.canonical', priority=10)

    # Red Hat Workday jobs
    register('redhat.wd5.myworkdayjobs.com', 'sites.redhat', priority=10)

    # Generic company domain matchers (lower priority)
    for domain, name in [
        ('nvidia.com', 'NVIDIA'),
    ]:
        lower = domain.lower()
        register_fn(lambda u, d=lower: d in u.lower(), 'sites.generic', priority=0)


def get_adapter(url: str) -> Optional[Callable]:
    """Find the best adapter for this URL. Returns None if no specific adapter."""
    _ensure_registered()
    sorted_adapters = sorted(_ADAPTERS, key=lambda x: -x[2])  # highest priority first
    for match_fn, module_name, _ in sorted_adapters:
        if match_fn(url):
            try:
                mod = importlib.import_module(module_name)
                if hasattr(mod, 'extract'):
                    return mod.extract
            except (ImportError, AttributeError) as e:
                logger.warning(f"Failed to load adapter {module_name}: {e}")
    return None


def known_companies() -> Dict[str, str]:
    """Return dict: url_substring -> company_name for URL-to-company fallback."""
    return {
        'google.com/about/careers': 'Google',
        'google.com': 'Google',
        'linkedin.com/jobs': 'LinkedIn',
        'linkedin.com': 'LinkedIn',
        'indeed.com': 'Indeed',
        'nvidia.com': 'NVIDIA',
        'microsoft.com': 'Microsoft',
        'apple.com': 'Apple',
        'amazon.jobs': 'Amazon',
        'amazon.com': 'Amazon',
        'meta.com': 'Meta',
        'ibm.com': 'IBM',
        'remoteok.com': 'RemoteOK',
        'weworkremotely.com': 'We Work Remotely',
        'greenhouse.io': 'Greenhouse',
        'lever.co': 'Lever',
    }
