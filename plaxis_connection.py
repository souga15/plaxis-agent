import logging

logger = logging.getLogger(__name__)

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
            cls._instance._host = "localhost"
            cls._instance._port_i = 10000
            cls._instance._port_o = 10001
            cls._instance._password = ""
        return cls._instance

    def connect(self, host="localhost", port_i=10000, port_o=10001, password=""):
        self._host = host
        self._port_i = port_i
        self._port_o = port_o
        self._password = password

        # Lazy import: allows the app to start even when plxscripting is not installed
        try:
            from plxscripting.easy import new_server
        except ImportError:
            logger.error(
                "plxscripting package is not installed. "
                "Install it from your Plaxis installation or via pip."
            )
            self.is_connected = False
            return False

        try:
            logger.info(f"Connecting to Plaxis Input server at {host}:{port_i}...")
            self.s_i, self.g_i = new_server(host, port_i, password=password)
            logger.info("Connected to Plaxis Input server.")

            try:
                logger.info(f"Connecting to Plaxis Output server at {host}:{port_o}...")
                self.s_o, self.g_o = new_server(host, port_o, password=password)
                logger.info("Connected to Plaxis Output server.")
            except Exception as e:
                logger.warning(f"Could not connect to Output server: {e}. Output features will be disabled.")
                self.s_o, self.g_o = None, None

            self.is_connected = True
            return True
        except Exception as e:
            logger.error(f"Failed to connect to Plaxis: {e}")
            self.is_connected = False
            return False

    def reconnect(self):
        """Reconnect using previously stored connection parameters."""
        logger.info("Attempting to reconnect to Plaxis...")
        # Reset state
        self.s_i = None
        self.g_i = None
        self.s_o = None
        self.g_o = None
        self.is_connected = False
        return self.connect(self._host, self._port_i, self._port_o, self._password)

    def get_input(self):
        if not self.is_connected or self.g_i is None:
            raise ConnectionError(
                "Not connected to Plaxis Input server. "
                "Make sure Plaxis 3D is open with Expert > Configure remote scripting server enabled on port 10000."
            )
        return self.s_i, self.g_i

    def get_output(self):
        if not self.is_connected or self.g_o is None:
            raise ConnectionError(
                "Not connected to Plaxis Output server. "
                "Make sure the Output program is open with scripting enabled on port 10001."
            )
        return self.s_o, self.g_o

    def call_command(self, command: str, server: str = "input"):
        """
        Execute a native PLAXIS command string through the scripting server.

        This is a compatibility fallback for cases where a Python wrapper
        attribute/command is unavailable in a given PLAXIS version but the
        native command line command still exists.
        """
        if server == "output":
            s, _ = self.get_output()
        else:
            s, _ = self.get_input()
        return s.call_and_handle_command(command)

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
            'Surfaces', 'Volumes', 'Boreholes', 'Soillayers',
            'Plates', 'EmbeddedBeams', 'Anchors', 'Geogrids',
            'SoilMat', 'PlateMat', 'AnchorMat', 'GeoMat',
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

connection_manager = PlaxisConnection()
