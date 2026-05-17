import logging
from plxscripting.easy import new_server

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

    def find_object_by_name(self, name: str):
        """
        Find a Plaxis object by its name across common collections.
        This is the correct way to look up objects (not getattr).
        
        Args:
            name: The Plaxis object name (e.g., 'Surface_1', 'Plate_1', 'Phase_1')
        
        Returns:
            The Plaxis object if found.
        
        Raises:
            ValueError: If the object is not found in any collection.
        """
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
                    try:
                        obj_name = obj.Name.value if hasattr(obj.Name, 'value') else str(obj.Name)
                    except Exception:
                        obj_name = str(obj)
                    if obj_name == name:
                        return obj
            except Exception:
                continue

        raise ValueError(
            f"Object '{name}' not found in any Plaxis collection. "
            f"Check the exact name in the Plaxis Model Explorer."
        )

connection_manager = PlaxisConnection()
