import os
import logging

logger = logging.getLogger(__name__)

COMPATIBILITY_ERROR_HINT = (
    "This usually means the connected PLAXIS scripting API does not match what this "
    "agent expects. Verify you are using a supported PLAXIS installation with Remote "
    "Scripting enabled and a matching official 'plxscripting' package."
)

class MockPlaxisObject:
    def __init__(self, name):
        class MockVal:
            def __init__(self, v): self.value = v
        self.Name = MockVal(name)
        self.Identification = MockVal(name)
        self.BoundingBox = (0.0, 0.0, 0.0, 1.0, 1.0, 1.0)
        
class MockPlaxisServer:
    def __init__(self):
        self.is_simulated = True
        self.Phases = [MockPlaxisObject("InitialPhase")]
        self.Surfaces = []
        self.Volumes = []
        self.Plates = []
        self.reset_model_state()

    def reset_model_state(self):
        self.has_excavation = False
        self.excavation_depth = 100 # y position in SVG
        self.has_retaining_wall = False
        self.has_anchors = False
        self.has_piles = False
        self.layers_list = [
            {"name": "Sand Layer (Unsat)", "thickness": 90, "color": "sand"},
            {"name": "Silt Layer (Water Level)", "thickness": 110, "color": "silt"},
            {"name": "Deep Clay Layer (Consolidation)", "thickness": 120, "color": "clay"}
        ]

    def __getattr__(self, name):
        def mock_func(*args, **kwargs):
            name_lower = name.lower()
            if name_lower == "getresults":
                return [1.32]  # Safe simulated FoS
            elif name_lower in ("plate", "create_plate"):
                self.has_retaining_wall = True
            elif name_lower in ("nodetonode", "create_anchor"):
                self.has_anchors = True
            elif name_lower in ("embeddedbeam", "create_pile"):
                self.has_piles = True
            elif name_lower in ("deactivate", "excavate"):
                self.has_excavation = True
            elif name_lower in ("new", "newproject", "new_project"):
                self.reset_model_state()
            return MockPlaxisObject(f"Mock_{name}")
        return mock_func

    def call_and_handle_command(self, cmd):
        cmd_lower = cmd.lower()
        if "plate" in cmd_lower:
            self.has_retaining_wall = True
        elif "nodetonode" in cmd_lower:
            self.has_anchors = True
        elif "embeddedbeam" in cmd_lower:
            self.has_piles = True
        elif "deactivate" in cmd_lower or "excavate" in cmd_lower:
            self.has_excavation = True
        elif "new" in cmd_lower or "newproject" in cmd_lower:
            self.reset_model_state()
        return f"[SIMULATED] {cmd}"

class PlaxisConnection:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(PlaxisConnection, cls).__new__(cls)
            cls._instance.s_i = None
            cls._instance.g_i = None
            cls._instance.s_o = None
            cls._instance.g_o = None
            cls._instance.is_connected = False
            cls._instance.is_simulation = False
            cls._instance._host = "localhost"
            cls._instance._port_i = 10000
            cls._instance._port_o = 10001
            cls._instance._password = ""
        return cls._instance

    def _enable_simulation_mode(self):
        logger.info("Entering PLAXIS Simulation Mode...")
        self.is_connected = True
        self.is_simulation = True
        self.g_i = MockPlaxisServer()
        self.s_i = self.g_i
        self.g_o = MockPlaxisServer()
        self.s_o = self.g_o

    def connect(self, host="localhost", port_i=10000, port_o=10001, password=""):
        self._host = host
        self._port_i = port_i
        self._port_o = port_o
        self._password = password
        self.is_simulation = False

        force_sim = os.getenv("PLAXIS_SIMULATION_MODE", "false").lower() == "true"
        if force_sim:
            logger.info("PLAXIS_SIMULATION_MODE=true. Forcing simulation mode.")
            self._enable_simulation_mode()
            return True

        try:
            from plxscripting.easy import new_server
        except ImportError:
            logger.warning("plxscripting not installed. Auto-falling back to Simulation Mode.")
            self._enable_simulation_mode()
            return True

        try:
            logger.info(f"Connecting to Plaxis Input server at {host}:{port_i}...")
            self.s_i, self.g_i = new_server(host, port_i, password=password)
            logger.info("Connected to Plaxis Input server.")

            try:
                self.s_o, self.g_o = new_server(host, port_o, password=password)
            except Exception as e:
                logger.warning(f"Could not connect to Output server: {e}. Output features disabled.")
                self.s_o, self.g_o = None, None

            self.is_connected = True
            return True
        except Exception as e:
            logger.warning(f"Failed to connect to Plaxis: {e}. Auto-falling back to Simulation Mode.")
            self._enable_simulation_mode()
            return True

    def reconnect(self):
        """Reconnect using previously stored connection parameters."""
        logger.info("Attempting to reconnect to Plaxis...")
        self.s_i = self.g_i = self.s_o = self.g_o = None
        self.is_connected = False
        self.is_simulation = False
        return self.connect(self._host, self._port_i, self._port_o, self._password)

    def get_input(self):
        if not self.is_connected or self.g_i is None:
            raise ConnectionError("Not connected to Plaxis Input server.")
        return self.s_i, self.g_i

    def get_output(self):
        if not self.is_connected:
            raise ConnectionError("Not connected to Plaxis. Run a project first.")
        if self.g_o is None:
            raise ConnectionError(
                "Plaxis Output server (port 10001) is not available. "
                "Make sure a calculation has been run and PLAXIS Output is open. "
                "Results extraction will be skipped."
            )
        return self.s_o, self.g_o

    def call_command(self, command: str, server: str = "input"):
        """Execute native PLAXIS command string through scripting server."""
        s, _ = self.get_output() if server == "output" else self.get_input()
        result = s.call_and_handle_command(command)
        if getattr(s, "is_simulated", False):
            return f"[SIMULATED] {command}"
        return result

    @staticmethod
    def classify_runtime_issue(error) -> str | None:
        """
        Return a user-facing compatibility explanation for common PLAXIS
        scripting API mismatches, or None when the error looks unrelated.
        """
        message = str(error)
        lowered = message.lower()

        compatibility_markers = [
            "requested attribute",
            "is not present",
            "incorrect or unspecified action",
            "call_and_handle_command",
        ]
        if any(marker in lowered for marker in compatibility_markers):
            return (
                f"Incompatible or unsupported PLAXIS scripting command/interface: {message}. "
                f"{COMPATIBILITY_ERROR_HINT}"
            )

        if "is not recognized as a global command" in lowered:
            return (
                f"PLAXIS rejected the command: {message}. This can happen when no project is open yet "
                f"(PLAXIS is still on the Start Page), or when the connected PLAXIS scripting API does not "
                f"support the command syntax this agent used. Verify a project is open first, then confirm "
                f"your PLAXIS version and official 'plxscripting' package match."
            )

        if "max retries exceeded" in lowered or "connection refused" in lowered or "winerror 10061" in lowered:
            return (
                "Cannot reach the Plaxis Output server (port 10001). "
                "This is expected if no calculation phase has been run yet, or if PLAXIS Output is not open. "
                "Please run a calculation first (generate mesh → add phase → run_calculation), then retry results extraction."
            )

        if "output server" in lowered and "not available" in lowered:
            return (
                "Plaxis Output server is not available. Run a calculation first before extracting results."
            )

        if "invalid parameters" in lowered:
            return (
                f"PLAXIS returned 'Invalid parameters': {message}. "
                "This usually means the command was issued with wrong argument order or type. "
                "The agent will automatically retry using an alternative command path."
            )

        return None

    @staticmethod
    def _safe_attr(obj, attr_name: str):
        """Safely read a Plaxis proxy attribute, returning None on failure."""
        try:
            val = getattr(obj, attr_name, None)
            if val is None:
                return None
            return val.value if hasattr(val, 'value') else str(val)
        except Exception:
            return None

    def find_object_by_name(self, name: str, server: str = "input"):
        """
        Find a Plaxis object by its Name or Identification across common collections.

        Args:
            name: The Plaxis object name or identification string
                  (e.g., 'Surface_1', 'Plate_1', 'Phase_1', or a user-set display name).
            server: Which Plaxis server to search — "input" (default) or "output".
                    Use "output" when querying results so the returned object belongs
                    to the Output server's object tree.

        Returns:
            The Plaxis object if found.

        Raises:
            ValueError: If the object is not found in any collection.
        """
        if server == "output":
            _, g = self.get_output()
        else:
            _, g = self.get_input()

        # Search through all common Plaxis object collections
        collections = [
            'Surfaces', 'Volumes', 'Boreholes', 'Soillayers', 'Soils',
            'Plates', 'EmbeddedBeams', 'Anchors', 'Geogrids',
            'SoilMat', 'PlateMat', 'AnchorMat', 'GeoMat', 'Materials',
            'Phases', 'PointLoads', 'LineLoads', 'SurfaceLoads',
            'Points', 'Lines', 'Polygons',
        ]

        for collection_name in collections:
            collection = getattr(g, collection_name, None)
            if collection is None:
                continue
            try:
                for obj in collection:
                    obj_name = self._safe_attr(obj, "Name")
                    obj_id = self._safe_attr(obj, "Identification")
                    if name in (obj_name, obj_id):
                        return obj
            except Exception:
                continue

        raise ValueError(
            f"Object '{name}' not found in any Plaxis collection. "
            f"Check the exact name in the Plaxis Model Explorer."
        )

    def find_object_by_coordinates(self, x: float, y: float, z: float, collection_name: str = "Volumes", tolerance: float = 0.01, server: str = "input"):
        """
        Find a Plaxis object by its physical coordinates using the BoundingBox property.
        
        Args:
            x, y, z: Target coordinates.
            collection_name: Plaxis collection to search (e.g., 'Volumes', 'Surfaces', 'Points').
            tolerance: Spatial tolerance for bounding box match.
        """
        if server == "output":
            _, g = self.get_output()
        else:
            _, g = self.get_input()
            
        collection = getattr(g, collection_name, None)
        if collection is None:
            raise ValueError(f"Collection '{collection_name}' not found.")
            
        for obj in collection:
            try:
                bbox = obj.BoundingBox
                if bbox is None:
                    continue
                # BoundingBox returns (xMin, yMin, zMin, xMax, yMax, zMax)
                x_min, y_min, z_min, x_max, y_max, z_max = bbox
                
                if (x_min - tolerance <= x <= x_max + tolerance and
                    y_min - tolerance <= y <= y_max + tolerance and
                    z_min - tolerance <= z <= z_max + tolerance):
                    return obj
            except Exception:
                continue
                
        raise ValueError(f"No object in {collection_name} found matching coordinates ({x}, {y}, {z})")

connection_manager = PlaxisConnection()
