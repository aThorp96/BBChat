import sys
import json

sys.path.append("../")
from bb84.bb84 import bb84

# Com Headers
Q_KEYGEN = 5
KEYGEN_OK = 10
C_MESSAGE = 20


class Client:
    key_map = {}

    def __init__(self, initiator, key_length, node_name="Alice", q_logger=print):
        # For now use a key for a default recipient, "Bob"
        self.tx_classical = node_name + "t"
        self.rx_classical = node_name + "r"
        self.node_name = node_name
        self.q_logger = q_logger
        if not initiator:
            self.recv_keygen("Alice")

    def initiate_keygen(self, recipient):
        k = bb84.initiate_keygen(
            name=self.node_name, recipient=recipient, q_logger=self.q_logger
        )
        self.key_map[self.recipient] = k

    def recv_keygen(self, initiator):
        k = bb84.target_keygen(name=self.node_name, initiator=initiator)
        self.key_map[self.recipient] = k

    def send_message(self, recipient, message):
        # Ensure we've co-generated a key
        if recipient not in self.key_map:
            self.q_logger("Initializing key")
            self.initiate_keygen(recipient)

        key = self.key_map[recipient]
        encrypted = bb84.encrypt(message, key)
        with CQCConnection(self.tx_classical) as cqc:
            cqc.sendClassical(recipient + "r", encrypted)

    def listener(self):
        with CQCConnection(self.rx_classical) as rx:
            message = rx.recvClassical().decode("utf8")
