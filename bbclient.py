import sys
import array
import json
import logging
import queue
from cqc.pythonLib import CQCConnection
from threading import Thread

sys.path.append("../")
from bb84.bb84 import bb84

# Com Headers
Q_KEYGEN = 5
KEYGEN_OK = 10
MESSAGE = 20

_log = logging.getLogger("BBChat")


class Client(Thread):
    key_map = {}

    def __init__(self, key_length, message_add, node_name="Alice", q_logger=print):
        # For now use a key for a default recipient, "Bob"
        Thread.__init__(self)
        self.node_name = node_name
        self.q_logger = q_logger
        self.message_add = message_add
        self.msg_queue = queue.Queue()
        self.start()

    def run(self):
        self.running = True
        while self.running:
            self.q_logger("Running!")
            if not self.msg_queue.empty():
                msg = self.msg_queue.get()
                self._send_message(msg["recipient"], msg["body"])
            else:
                self._check_messages()

    def _initiate_keygen(self, recipient):
        init_msg = {"code": Q_KEYGEN, "sender": self.node_name}
        with bb84.get_CQCConnection(self.node_name) as cqc:
            cqc.sendClassical(recipient, json.dumps(init_msg).encode())

        try:
            k = bb84.initiate_keygen(
                name=self.node_name, recipient=recipient, q_logger=self.q_logger
            )
            self.key_map[recipient] = k
        except bb84.PoorErrorRate as e:
            self.q_logger("Bad error rate. Attempting again")
            self._initiate_keygen(recipient)

    def _recv_keygen(self, initiator):
        self.q_logger("Recieving keygen")
        try:
            k = bb84.target_keygen(
                name=self.node_name, initiator=initiator, q_logger=self.q_logger
            )
            self.key_map[initiator] = k
        except bb84.PoorErrorRate as e:
            self.q_logger("Bad error rate. Attempting again")
            self._recv_keygen(initiator)

    def send_message(self, recipient, message):
        self.msg_queue.put({"recipient": recipient, "body": message})
        bb84.get_CQCConnection(self.node_name).closeClassicalServer()

    def _send_message(self, recipient, message):
        # Ensure we've co-generated a key
        if recipient not in self.key_map:
            self.q_logger("Initializing key")
            self._initiate_keygen(recipient)

        key = self.key_map[recipient]
        packet = json.dumps({"code": MESSAGE, "sender": self.node_name})

        self.q_logger("Encrypting message")
        encrypted = bb84.encrypt(message, int(key))

        with bb84.get_CQCConnection(self.node_name) as cqc:
            self.q_logger("Transmitting message")
            cqc.sendClassical(recipient, bytearray(packet, "utf-8"))
            self.q_logger("Header sent")
            cqc.sendClassical(recipient, encrypted)
            self.q_logger("Message sent")

    def _recv_message(self, sender, body):
        key = self.key_map[sender]
        message = bb84.decrypt(body, int(key))
        self.message_add((sender, message.decode("utf-8")))

    def _check_messages(self):
        message = None
        try:
            # Check for messages
            with bb84.get_CQCConnection(self.node_name) as rx:
                self.q_logger("Attempting to receive new messages")
                m = rx.recvClassical(timout=1).decode("utf-8")
                self.q_logger("Received new messages")
                message = json.loads(m)
            self.q_logger("Got past message check")
            # Check message type
            if message.get("code") == Q_KEYGEN:
                self._recv_keygen(message["sender"])
            elif message.get("code") == MESSAGE:
                self.q_logger("Incoming message from {}".format(message["sender"]))
                with bb84.get_CQCConnection(self.node_name) as rx:
                    body = rx.recvClassical()
                self._recv_message(message["sender"], body)

        except Exception as e:
            # self.q_logger("Exception: {}".format(e))
            _log.debug(e)

    def exit(self):
        # TODO figure out how the hell to close this...
        bb84.get_CQCConnection(self.node_name).exit()
        self.running = False
        self.join()
