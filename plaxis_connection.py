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
        return cls._instance

    def connect(self, host="localhost", port_i=10000, port_o=10001, password=""):
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

    def get_input(self):
        if not self.is_connected or self.g_i is None:
            raise ConnectionError("Not connected to Plaxis Input server.")
        return self.s_i, self.g_i

    def get_output(self):
        if not self.is_connected or self.g_o is None:
            raise ConnectionError("Not connected to Plaxis Output server.")
        return self.s_o, self.g_o

connection_manager = PlaxisConnection()
