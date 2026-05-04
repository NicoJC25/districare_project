import logging
import threading
import time

from simulator.ambulance_node.node_client import AmbulanceNodeClient

logger = logging.getLogger(__name__)


class HeartbeatLoop:
    def __init__(self, client: AmbulanceNodeClient, interval_seconds: int):
        self.client = client
        self.interval_seconds = interval_seconds
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)

    def start(self) -> None:
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self.client.heartbeat()
                logger.info("Heartbeat enviado por %s", self.client.code)
            except Exception as exc:
                logger.warning("No se pudo enviar heartbeat: %s", exc)
            time.sleep(self.interval_seconds)
