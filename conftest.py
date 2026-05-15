# The repo-root __init__.py is the ComfyUI package entrypoint and uses
# package-relative imports; pytest must not try to collect/import it.
collect_ignore = ["__init__.py"]
