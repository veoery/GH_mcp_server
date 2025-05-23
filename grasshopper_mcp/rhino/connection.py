import platform
import os
import json
import uuid
from typing import Any, Dict, List, Optional
import time
import platform
import sys
import socket
import tempfile

from ..config import ServerConfig


def find_scriptcontext_path():
    scriptcontext_path = os.path.join(
        os.environ["APPDATA"],
        "McNeel",
        "Rhinoceros",
        "7.0",
        "Plug-ins",
        "IronPython (814d908a-e25c-493d-97e9-ee3861957f49)",
        "settings",
        "lib",
    )

    if not os.path.exists(scriptcontext_path):
        # If the specific path doesn't exist, try to find it
        import glob

        appdata = os.environ["APPDATA"]
        potential_paths = glob.glob(
            os.path.join(appdata, "McNeel", "Rhinoceros", "7.0", "Plug-ins", "IronPython*", "settings", "lib")
        )
        if potential_paths:
            scriptcontext_path
            # sys.path.append(potential_paths[0])

    return scriptcontext_path


def find_RhinoPython_path(rhino_path):
    appdata = os.environ["APPDATA"]
    rhino_python_paths = [
        # Standard Rhino Python lib paths
        os.path.join(os.path.dirname(rhino_path), "Plug-ins", "IronPython"),
        os.path.join(os.path.dirname(rhino_path), "Plug-ins", "IronPython", "Lib"),
        os.path.join(os.path.dirname(rhino_path), "Plug-ins", "PythonPlugins"),
        os.path.join(os.path.dirname(rhino_path), "Scripts"),
        # Try to find RhinoPython in various locations
        os.path.join(os.path.dirname(rhino_path), "Plug-ins"),
        os.path.join(appdata, "McNeel", "Rhinoceros", "7.0", "Plug-ins"),
        os.path.join(appdata, "McNeel", "Rhinoceros", "7.0", "Scripts"),
        # Common Rhino installation paths for plugins
        "C:\\Program Files\\Rhino 7\\Plug-ins",
        "C:\\Program Files\\Rhino 7\\Plug-ins\\PythonPlugins",
    ]

    return rhino_python_paths


class RhinoConnection:
    """Connection to Rhino/Grasshopper."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.connected = False
        self.rhino_instance = None
        self.is_mac = platform.system() == "Darwin"

        self.codelistener_host = "127.0.0.1"
        self.codelistener_port = 614  # Default CodeListener port

    async def initialize(self) -> None:
        """Initialize connection to Rhino/Grasshopper."""
        if self.config.use_compute_api:
            # Setup compute API connection
            self._initialize_compute()
        else:
            # Setup direct connection
            self._initialize_rhino()

        self.connected = True

    def _initialize_rhino(self) -> None:
        """Initialize Rhino geometry access."""
        if platform.system() == "Windows" and not self.config.use_rhino3dm:
            # Windows-specific RhinoInside implementation
            import sys

            rhino_path = self.config.rhino_path

            if not rhino_path or not os.path.exists(rhino_path):
                raise ValueError(f"Invalid Rhino path: {rhino_path}")
            # print(rhino_path)
            sys.path.append(rhino_path)

            # Add the specific path for scriptcontext
            scriptcontext_path = find_scriptcontext_path()
            sys.path.append(scriptcontext_path)

            RhinoPython_path = find_RhinoPython_path(rhino_path)
            for path in RhinoPython_path:
                if os.path.exists(path):
                    sys.path.append(path)
                    print(path)

            try:
                import rhinoinside

                rhinoinside.load()
                print("rhinoinside installed.")
                # Import Rhino components
                import Rhino

                print("Rhino installed.")
                import Rhino.Geometry as rg

                print("Rhino.Geometry installed.")
                import scriptcontext as sc

                # Store references
                self.rhino_instance = {"Rhino": Rhino, "rg": rg, "sc": sc, "use_rhino3dm": False}
            except ImportError as e:
                raise ImportError(f"Error importing RhinoInside or Rhino components: {e}")
        else:
            # Cross-platform rhino3dm implementation
            try:
                import rhino3dm as r3d

                self.rhino_instance = {"r3d": r3d, "use_rhino3dm": True}
            except ImportError:
                raise ImportError("Please install rhino3dm: uv add rhino3dm")

    async def send_code_to_rhino(self, code: str) -> Dict[str, Any]:
        """Send Python code to Rhino via CodeListener.

        Args:
            code: Python code to execute in Rhino

        Returns:
            Dictionary with result and response or error
        """
        try:
            # Create a temporary Python file
            fd, temp_path = tempfile.mkstemp(suffix=".py")
            try:
                # Write the code to the file
                with os.fdopen(fd, "w") as f:
                    f.write(code)

                # Create message object
                msg_obj = {"filename": temp_path, "run": True, "reset": False, "temp": True}

                # Convert to JSON
                json_msg = json.dumps(msg_obj)

                # Create a TCP socket
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(10)
                sock.connect((self.codelistener_host, self.codelistener_port))

                # Send the JSON message
                sock.sendall(json_msg.encode("utf-8"))

                # Receive the response
                response = sock.recv(4096).decode("utf-8")

                # Close the socket
                sock.close()

                return {"result": "success", "response": response}

            finally:
                # Clean up - remove temporary file after execution
                try:
                    os.unlink(temp_path)
                except Exception as cleanup_error:
                    print(f"Error cleaning up temporary file: {cleanup_error}")

        except Exception as e:
            return {"result": "error", "error": str(e)}

    async def generate_and_execute_rhino_code(
        self, prompt: str, model_context: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate Rhino Python code from a prompt and execute it.

        Args:
            prompt: Description of what code to generate
            model_context: Optional context about the model (dimensions, parameters, etc.)

        Returns:
            Result dictionary with code, execution result, and any output
        """
        # Step 1: Generate Python code based on the prompt
        code = await self._generate_code_from_prompt(prompt, model_context)

        # Step 2: Execute the generated code in Rhino
        result = await self.send_code_to_rhino(code)

        # Return both the code and the execution result
        return {
            "result": result.get("result", "error"),
            "code": code,
            "response": result.get("response", ""),
            "error": result.get("error", ""),
        }

    async def _generate_code_from_prompt(
        self, prompt: str, model_context: Optional[Dict[str, Any]] = None
    ) -> str:
        """Generate Rhino Python code from a text prompt.

        Args:
            prompt: Description of what the code should do
            model_context: Optional context about the model

        Returns:
            Generated Python code as a string
        """
        # Add standard imports for Rhino Python code
        code = """
import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import System
from Rhino.Geometry import *

# Disable redraw to improve performance
rs.EnableRedraw(False)
"""

        # Add code based on the prompt
        prompt_lower = prompt.lower()

        if "circle" in prompt_lower:
            radius = model_context.get("radius", 10.0) if model_context else 10.0
            center_x = model_context.get("center_x", 0.0) if model_context else 0.0
            center_y = model_context.get("center_y", 0.0) if model_context else 0.0
            center_z = model_context.get("center_z", 0.0) if model_context else 0.0
            code += f"""
# Create a circle based on prompt: {prompt}
center = Point3d({center_x}, {center_y}, {center_z})
circle = Circle(Plane.WorldXY, center, {radius})
circle_id = sc.doc.Objects.AddCircle(circle)
if circle_id:
    rs.ObjectName(circle_id, "GeneratedCircle")
    print("Created a circle!")
else:
    print("Failed to create circle")
"""
        return code

    async def send_code_to_gh(self, code: str, file_path: str) -> Dict[str, Any]:
        """Send Python code to a file for Grasshopper to use.

        Args:
            code: Python code to save for Grasshopper
            file_path: Path where the Python file should be saved

        Returns:
            Dictionary with result and file path
        """
        try:
            # Write the code to the file
            with open(file_path, "w") as f:
                f.write(code)

            return {
                "result": "success",
                "file_path": file_path,
                "message": f"Grasshopper Python file created at {file_path}",
            }

        except Exception as e:
            return {"result": "error", "error": str(e)}

    async def generate_and_execute_gh_code(
        self,
        prompt: str,
        file_path: str,
        model_context: Optional[Dict[str, Any]] = None,
        component_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Generate Grasshopper Python code from a prompt and save it for execution.

        Args:
            prompt: Description of what code to generate
            model_context: Optional context about the model (dimensions, parameters, etc.)
            component_name: Optional name for the GH Python component

        Returns:
            Result dictionary with code, file path, and any output
        """
        # Step 1: Generate Python code based on the prompt
        code = await self._generate_gh_code_from_prompt(prompt, model_context, component_name)

        # Step 2: Save the generated code for Grasshopper to use
        result = await self.send_code_to_gh(code, file_path)

        # Return both the code and the result
        return {
            "result": result.get("result", "error"),
            "code": code,
            "file_path": result.get("file_path", ""),
            "response": result.get("response", ""),
            "error": result.get("error", ""),
        }

    async def _generate_gh_code_from_prompt(
        self,
        prompt: str,
        model_context: Optional[Dict[str, Any]] = None,
        component_name: Optional[str] = None,
    ) -> str:
        """Generate Grasshopper Python code from a text prompt.

        Args:
            prompt: Description of what the code should do
            model_context: Optional context about the model
            component_name: Optional name for the component

        Returns:
            Generated Python code as a string
        """
        # Add component name as a comment
        if component_name:
            code = f"""# Grasshopper Python Component: {component_name}
# Generated from prompt: {prompt}
"""
        else:
            code = f"""# Grasshopper Python Component
# Generated from prompt: {prompt}
"""

        # Add standard imports for Grasshopper Python code
        code += """
import Rhino
import rhinoscriptsyntax as rs
import scriptcontext as sc
import Rhino.Geometry as rg
import ghpythonlib.components as ghcomp
import math
"""
        # Add code based on the prompt
        prompt_lower = prompt.lower()

        if "circle" in prompt_lower:
            radius = model_context.get("radius", 10.0) if model_context else 10.0
            center_x = model_context.get("center_x", 0.0) if model_context else 0.0
            center_y = model_context.get("center_y", 0.0) if model_context else 0.0
            center_z = model_context.get("center_z", 0.0) if model_context else 0.0
            code += f"""
# Create a circle based on prompt: {prompt}
center = rg.Point3d({center_x}, {center_y}, {center_z})
circle = rg.Circle(rg.Plane.WorldXY, center, {radius})
print("Created a circle!")
"""
        return code

    def _initialize_compute(self) -> None:
        """Initialize connection to compute.rhino3d.com."""
        if not self.config.compute_url or not self.config.compute_api_key:
            raise ValueError("Compute API URL and key required for compute API connection")

        # We'll use requests for API calls

    async def close(self) -> None:
        """Close connection to Rhino/Grasshopper."""
        # Cleanup as needed
        self.connected = False

    async def execute_code(self, code: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute operations on Rhino geometry."""
        if not self.connected:
            raise RuntimeError("Not connected to Rhino geometry system")

        if self.config.use_compute_api:
            return await self._execute_compute(code, parameters)
        else:
            # Check if we're using rhino3dm
            if self.rhino_instance.get("use_rhino3dm", False):
                return await self._execute_rhino3dm(code, parameters)
            else:
                return await self._execute_rhino(code, parameters)

    async def _execute_rhino(self, code: str, parameters: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Execute code directly in Rhino (Windows only)."""
        # Existing Rhino execution code
        globals_dict = dict(self.rhino_instance)

        # Add parameters to context
        if parameters:
            globals_dict.update(parameters)

        # Execute the code
        locals_dict = {}
        try:
            exec(code, globals_dict, locals_dict)
            return {"result": "success", "data": locals_dict.get("result", None)}
        except Exception as e:
            # More detailed error reporting for Windows
            import traceback

            error_trace = traceback.format_exc()
            return {"result": "error", "error": str(e), "traceback": error_trace}

    async def _execute_rhino3dm(
        self, code: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute code using rhino3dm library."""
        # Create execution context with rhino3dm
        r3d = self.rhino_instance["r3d"]
        globals_dict = {"r3d": r3d, "parameters": parameters or {}}

        # Add parameters to context
        if parameters:
            globals_dict.update(parameters)

        # Execute the code
        locals_dict = {}
        try:
            exec(code, globals_dict, locals_dict)
            return {"result": "success", "data": locals_dict.get("result", None)}
        except Exception as e:
            return {"result": "error", "error": str(e)}

    async def _execute_compute(
        self, code: str, parameters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Execute code via compute.rhino3d.com API."""
        # Existing Compute API code
        import requests

        url = f"{self.config.compute_url}/grasshopper"

        # Prepare request payload
        payload = {"algo": code, "pointer": None, "values": parameters or {}}

        headers = {
            "Authorization": f"Bearer {self.config.compute_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return {"result": "success", "data": response.json()}
        except Exception as e:
            return {"result": "error", "error": str(e)}

    async def read_3dm_file(self, file_path: str) -> Dict[str, Any]:
        """Read a .3dm file and return its model."""
        if not self.connected:
            raise RuntimeError("Not connected to Rhino geometry system")

        try:
            if self.rhino_instance.get("use_rhino3dm", False):
                r3d = self.rhino_instance["r3d"]
                model = r3d.File3dm.Read(file_path)
                if model:
                    return {"result": "success", "model": model}
                else:
                    return {"result": "error", "error": f"Failed to open file: {file_path}"}
            else:
                # For RhinoInside on Windows, use a different approach
                code = """
                import Rhino
                result = {
                    "model": Rhino.FileIO.File3dm.Read(file_path)
                }
                """
                return await self._execute_rhino(code, {"file_path": file_path})
        except Exception as e:
            return {"result": "error", "error": str(e)}

    ### For Grasshopper
    async def create_gh_script_component(
        self, description: str, inputs: List[Dict[str, Any]], outputs: List[Dict[str, Any]], code: str
    ) -> Dict[str, Any]:
        """Create a Python script component in a Grasshopper definition.

        Args:
            description: Description of the component
            inputs: List of input parameters
            outputs: List of output parameters
            code: Python code for the component

        Returns:
            Result dictionary with component_id on success
        """
        if not self.connected:
            return {"result": "error", "error": "Not connected to Rhino/Grasshopper"}

        # Generate a unique component ID
        component_id = f"py_{str(uuid.uuid4())[:8]}"

        if self.config.use_compute_api:
            # Implementation for compute API
            return await self._create_gh_script_component_compute(
                component_id, description, inputs, outputs, code
            )
        elif platform.system() == "Windows" and not self.rhino_instance.get("use_rhino3dm", True):
            # Implementation for RhinoInside (Windows)
            return await self._create_gh_script_component_rhinoinside(
                component_id, description, inputs, outputs, code
            )
        else:
            # We can't directly create Grasshopper components with rhino3dm
            return {
                "result": "error",
                "error": "Creating Grasshopper components requires RhinoInside or Compute API",
            }

    async def _create_gh_script_component_rhinoinside(
        self,
        component_id: str,
        description: str,
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]],
        code: str,
    ) -> Dict[str, Any]:
        """Create a Python script component using RhinoInside."""
        # Using the RhinoInside context
        execution_code = """
        import Rhino
        import Grasshopper
        import GhPython
        from Grasshopper.Kernel import GH_Component
        
        # Access the current Grasshopper document
        gh_doc = Grasshopper.Instances.ActiveCanvas.Document
        
        # Create a new Python component
        py_comp = GhPython.Component.PythonComponent()
        py_comp.NickName = description
        py_comp.Name = description
        py_comp.Description = description
        py_comp.ComponentGuid = System.Guid(component_id)
        
        # Set up inputs
        for i, inp in enumerate(inputs):
            name = inp["name"]
            param_type = inp.get("type", "object")
            # Convert param_type to Grasshopper parameter type
            access_type = 0  # 0 = item access
            py_comp.Params.Input[i].Name = name
            py_comp.Params.Input[i].NickName = name
            py_comp.Params.Input[i].Description = inp.get("description", "")
        
        # Set up outputs
        for i, out in enumerate(outputs):
            name = out["name"]
            param_type = out.get("type", "object")
            # Convert param_type to Grasshopper parameter type
            py_comp.Params.Output[i].Name = name
            py_comp.Params.Output[i].NickName = name
            py_comp.Params.Output[i].Description = out.get("description", "")
        
        # Set the Python code
        py_comp.ScriptSource = code
        
        # Add the component to the document
        gh_doc.AddObject(py_comp, False)
        
        # Set the position on canvas (centered)
        py_comp.Attributes.Pivot = Grasshopper.Kernel.GH_Convert.ToPoint(
            Rhino.Geometry.Point2d(gh_doc.Bounds.Center.X, gh_doc.Bounds.Center.Y)
        )
        
        # Update the document
        gh_doc.NewSolution(True)
        
        # Store component for reference
        result = {
            "component_id": str(component_id)
        }
        """

        # Execute the code
        return await self._execute_rhino(
            execution_code,
            {
                "component_id": component_id,
                "description": description,
                "inputs": inputs,
                "outputs": outputs,
                "code": code,
            },
        )

    async def _create_gh_script_component_compute(
        self,
        component_id: str,
        description: str,
        inputs: List[Dict[str, Any]],
        outputs: List[Dict[str, Any]],
        code: str,
    ) -> Dict[str, Any]:
        """Create a Python script component using Compute API."""
        import requests

        url = f"{self.config.compute_url}/grasshopper/scriptcomponent"

        # Prepare payload
        payload = {
            "id": component_id,
            "name": description,
            "description": description,
            "inputs": inputs,
            "outputs": outputs,
            "code": code,
        }

        headers = {
            "Authorization": f"Bearer {self.config.compute_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return {"result": "success", "component_id": component_id, "data": response.json()}
        except Exception as e:
            return {"result": "error", "error": str(e)}

    async def add_gh_component(
        self, component_name: str, component_type: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a component from an existing Grasshopper plugin.

        Args:
            component_name: Name of the component
            component_type: Type/category of the component
            parameters: Component parameters and settings

        Returns:
            Result dictionary with component_id on success
        """
        if not self.connected:
            return {"result": "error", "error": "Not connected to Rhino/Grasshopper"}

        # Generate a unique component ID
        component_id = f"comp_{str(uuid.uuid4())[:8]}"

        if self.config.use_compute_api:
            # Implementation for compute API
            return await self._add_gh_component_compute(
                component_id, component_name, component_type, parameters
            )
        elif platform.system() == "Windows" and not self.rhino_instance.get("use_rhino3dm", True):
            # Implementation for RhinoInside
            return await self._add_gh_component_rhinoinside(
                component_id, component_name, component_type, parameters
            )
        else:
            return {
                "result": "error",
                "error": "Adding Grasshopper components requires RhinoInside or Compute API",
            }

    async def _add_gh_component_rhinoinside(
        self, component_id: str, component_name: str, component_type: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a Grasshopper component using RhinoInside."""
        execution_code = """
        import Rhino
        import Grasshopper
        from Grasshopper.Kernel import GH_ComponentServer
        
        # Access the current Grasshopper document
        gh_doc = Grasshopper.Instances.ActiveCanvas.Document
        
        # Find the component by name and type
        server = GH_ComponentServer.FindServer(component_name, component_type)
        if server is None:
            raise ValueError(f"Component '{component_name}' of type '{component_type}' not found")
        
        # Create the component instance
        component = server.Create()
        component.ComponentGuid = System.Guid(component_id)
        
        # Set parameters
        for param_name, param_value in parameters.items():
            if hasattr(component, param_name):
                setattr(component, param_name, param_value)
        
        # Add the component to the document
        gh_doc.AddObject(component, False)
        
        # Set the position on canvas
        component.Attributes.Pivot = Grasshopper.Kernel.GH_Convert.ToPoint(
            Rhino.Geometry.Point2d(gh_doc.Bounds.Center.X, gh_doc.Bounds.Center.Y)
        )
        
        # Update the document
        gh_doc.NewSolution(True)
        
        # Return component info
        result = {
            "component_id": str(component_id)
        }
        """

        return await self._execute_rhino(
            execution_code,
            {
                "component_id": component_id,
                "component_name": component_name,
                "component_type": component_type,
                "parameters": parameters,
            },
        )

    async def _add_gh_component_compute(
        self, component_id: str, component_name: str, component_type: str, parameters: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Add a Grasshopper component using Compute API."""
        import requests

        url = f"{self.config.compute_url}/grasshopper/component"

        # Prepare payload
        payload = {
            "id": component_id,
            "name": component_name,
            "type": component_type,
            "parameters": parameters,
        }

        headers = {
            "Authorization": f"Bearer {self.config.compute_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return {"result": "success", "component_id": component_id, "data": response.json()}
        except Exception as e:
            return {"result": "error", "error": str(e)}

    async def connect_gh_components(
        self, source_id: str, source_param: str, target_id: str, target_param: str
    ) -> Dict[str, Any]:
        """Connect parameters between Grasshopper components.

        Args:
            source_id: Source component ID
            source_param: Source parameter name
            target_id: Target component ID
            target_param: Target parameter name

        Returns:
            Result dictionary
        """
        if not self.connected:
            return {"result": "error", "error": "Not connected to Rhino/Grasshopper"}

        if self.config.use_compute_api:
            return await self._connect_gh_components_compute(source_id, source_param, target_id, target_param)
        elif platform.system() == "Windows" and not self.rhino_instance.get("use_rhino3dm", True):
            return await self._connect_gh_components_rhinoinside(
                source_id, source_param, target_id, target_param
            )
        else:
            return {
                "result": "error",
                "error": "Connecting Grasshopper components requires RhinoInside or Compute API",
            }

    async def _connect_gh_components_rhinoinside(
        self, source_id: str, source_param: str, target_id: str, target_param: str
    ) -> Dict[str, Any]:
        """Connect Grasshopper components using RhinoInside."""
        execution_code = """
        import Rhino
        import Grasshopper
        from Grasshopper.Kernel import GH_Document
        
        # Access the current Grasshopper document
        gh_doc = Grasshopper.Instances.ActiveCanvas.Document
        
        # Find the source component
        source = None
        for obj in gh_doc.Objects:
            if str(obj.ComponentGuid) == source_id:
                source = obj
                break
        
        if source is None:
            raise ValueError(f"Source component with ID {source_id} not found")
        
        # Find the target component
        target = None
        for obj in gh_doc.Objects:
            if str(obj.ComponentGuid) == target_id:
                target = obj
                break
        
        if target is None:
            raise ValueError(f"Target component with ID {target_id} not found")
        
        # Find the source output parameter
        source_output = None
        for i, param in enumerate(source.Params.Output):
            if param.Name == source_param:
                source_output = param
                break
        
        if source_output is None:
            raise ValueError(f"Source parameter {source_param} not found on component {source_id}")
        
        # Find the target input parameter
        target_input = None
        for i, param in enumerate(target.Params.Input):
            if param.Name == target_param:
                target_input = param
                break
        
        if target_input is None:
            raise ValueError(f"Target parameter {target_param} not found on component {target_id}")
        
        # Connect the parameters
        gh_doc.GraftIO(source_output.Recipients, target_input.Sources)
        
        # Update the document
        gh_doc.NewSolution(True)
        
        result = {
            "success": True
        }
        """

        return await self._execute_rhino(
            execution_code,
            {
                "source_id": source_id,
                "source_param": source_param,
                "target_id": target_id,
                "target_param": target_param,
            },
        )

    async def _connect_gh_components_compute(
        self, source_id: str, source_param: str, target_id: str, target_param: str
    ) -> Dict[str, Any]:
        """Connect Grasshopper components using Compute API."""
        import requests

        url = f"{self.config.compute_url}/grasshopper/connect"

        # Prepare payload
        payload = {
            "source_id": source_id,
            "source_param": source_param,
            "target_id": target_id,
            "target_param": target_param,
        }

        headers = {
            "Authorization": f"Bearer {self.config.compute_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return {"result": "success", "data": response.json()}
        except Exception as e:
            return {"result": "error", "error": str(e)}

    async def run_gh_definition(
        self, file_path: Optional[str] = None, save_output: bool = False, output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run a Grasshopper definition.

        Args:
            file_path: Path to the .gh file (or None for current definition)
            save_output: Whether to save the output
            output_path: Path to save the output (if save_output is True)

        Returns:
            Result dictionary with execution information
        """
        if not self.connected:
            return {"result": "error", "error": "Not connected to Rhino/Grasshopper"}

        if self.config.use_compute_api:
            return await self._run_gh_definition_compute(file_path, save_output, output_path)
        elif platform.system() == "Windows" and not self.rhino_instance.get("use_rhino3dm", True):
            return await self._run_gh_definition_rhinoinside(file_path, save_output, output_path)
        else:
            return {
                "result": "error",
                "error": "Running Grasshopper definitions requires RhinoInside or Compute API",
            }

    async def _run_gh_definition_rhinoinside(
        self, file_path: Optional[str] = None, save_output: bool = False, output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run a Grasshopper definition using RhinoInside."""
        execution_code = """
        import Rhino
        import Grasshopper
        import time
        
        start_time = time.time()
        
        if file_path:
            # Open the specified Grasshopper definition
            gh_doc = Grasshopper.Kernel.GH_Document()
            gh_doc.LoadDocumentObject(file_path)
        else:
            # Use the current document
            gh_doc = Grasshopper.Instances.ActiveCanvas.Document
        
        # Run the solution
        gh_doc.NewSolution(True)
        
        # Wait for solution to complete
        while gh_doc.SolutionState != Grasshopper.Kernel.GH_ProcessStep.Finished:
            time.sleep(0.1)
        
        execution_time = time.time() - start_time
        
        # Save if requested
        if save_output and output_path:
            gh_doc.SaveAs(output_path, False)
        
        # Get a summary of the outputs
        output_summary = []
        for obj in gh_doc.Objects:
            if obj.Attributes.GetTopLevel.DocObject is not None:
                for param in obj.Params.Output:
                    if param.VolatileDataCount > 0:
                        output_summary.append({
                            "component": obj.NickName,
                            "param": param.Name,
                            "data_count": param.VolatileDataCount
                        })
        
        result = {
            "execution_time": execution_time,
            "output_summary": output_summary
        }
        """

        return await self._execute_rhino(
            execution_code, {"file_path": file_path, "save_output": save_output, "output_path": output_path}
        )

    async def _run_gh_definition_compute(
        self, file_path: Optional[str] = None, save_output: bool = False, output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """Run a Grasshopper definition using Compute API."""
        import requests

        url = f"{self.config.compute_url}/grasshopper/run"

        # Prepare payload
        payload = {"file_path": file_path, "save_output": save_output, "output_path": output_path}

        headers = {
            "Authorization": f"Bearer {self.config.compute_api_key}",
            "Content-Type": "application/json",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response.raise_for_status()
            return {"result": "success", "data": response.json()}
        except Exception as e:
            return {"result": "error", "error": str(e)}
