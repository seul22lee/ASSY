"""Single source of the code version.

Kept in its own module so runtime components can read it without importing the
package root, which would be circular.
"""

__version__ = "0.2.0"
