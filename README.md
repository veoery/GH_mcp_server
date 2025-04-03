# GH_mcp_server

GH_mcp_server provides an approach that allows designer to interact with Rhino and Grasshopper directly via LLMs, including to analyse .3dm file, do 3D modeling and generate GHPython automatically in Grasshopper based on user’s guidance.

## Requirements

- Rhino 7 or 8

- `uv`

  - ```
    # For MacOS and Linux
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```

  - ``````
    # For Windows
    powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
    ``````

## Installation

We recommend using `uv`:

### 1. Clone the repository

```
git clone git@github.com:veoery/GH_mcp_server.git
cd GH_mcp_server
```

------

### 2. Set up the environment

#### macOS/Linux

```
uv venv
source .venv/bin/activate
uv pip install -e .
```

#### Windows

```
uv venv
.venv\Scripts\activate
uv pip install -e .
```

> Make sure the virtual environment is activated before running or developing the project.

