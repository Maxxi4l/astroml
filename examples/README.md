# Example Notebooks Setup

Before running the example notebooks, install project dependencies from the repository root.

```bash
pip install -r requirements.txt
pip install -e .
```

If your notebook kernel is started from a different directory, make sure the repository root is on `sys.path` or change the working directory to the project root before importing `astroml`.

Example:

```python
import os
import sys
repo_root = os.path.abspath(os.path.join(os.getcwd(), ".."))
if repo_root not in sys.path:
    sys.path.insert(0, repo_root)
```
