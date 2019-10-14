import sys
import socket
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

    def __init__(
        self, initiator, key_length, message_add, node_name="Alice", q_logger=print
    ):
        # For now use a key for a default recipient, "Bob"
        Thread.__init__(self)
        self.initiator = initiator

        # Yeah.. if we would get rid of this code at some point, that'd be great..
        if self.initiator:
            self.recipient = "Bob"
        else:
            self.recipient = "Alice"

        self.node_name = node_name
        self.q_logger = q_logger
        self.message_add = message_add
        self.msg_queue = queue.Queue()
        self.listening = True
        self.start()

    def run(self):
        # Generate a key and then begin listining for messages
        try:
            if self.initiator:
                self._initiate_keygen(self.recipient)
            else:
                self._recv_keygen(self.recipient)
            self.q_logger("Fetching connection")

            cqc = bb84.get_CQCConnection(self.node_name)
            cqc.close()

            # Get connection to recipient
            addr = cqc._appNet.hostDict[self.recipient].addr
            self.conn = socket.socket(addr[0], addr[1], addr[2])

            self.message_add(("addr", addr[4]))
            self.conn.connect(addr[4])

            # main loop
            while self.listening:
                self.q_logger("Listening")
                self._check_messages()
        except Exception as e:
            self.message_add(("err", e))


    def _initiate_keygen(self, recipient):
        init_msg = {"code": Q_KEYGEN, "sender": self.node_name}
        # with bb84.get_CQCConnection(self.node_name) as cqc:
        # cqc.sendClassical(recipient, json.dumps(init_msg).encode())

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
        key = self.key_map[recipient]
        packet = json.dumps({"code": MESSAGE, "sender": self.node_name})

        self.q_logger("Encrypting message")
        encrypted = bb84.encrypt(message, int(key))

        self.q_logger("Transmitting message")
        # cqc.sendClassical(recipient, bytearray(packet, "utf-8"))
        self.q_logger("Header sent")
        self.conn.send(bytes(encrypted))
        self.q_logger("Message sent")

    def _recv_message(self, sender, body):
        key = self.key_map[sender]
        message = bb84.decrypt(body, int(key))
        self.message_add((sender, message.decode("utf-8")))

    def _check_messages(self):
        message = None
        try:
            # Check for messages
            self.q_logger("Listening for new stuff")
            rx_ready, tx_ready, _ = select.select([self.conn], [self.conn], [], 1)
            for rx in rx_ready:
                self.q_logger("rx ready")
                self.message_add(("rx: ", self.conn.recv(1024)))
            for tx in tx_ready:
                self.q_logger("tx ready")
                while self.msg_queue.not_empty():
                    msg = self.msg_queue.get()
                    self._send
                self.message_add(("rx: ", self.conn.recv(1024)))
            # Check message type
            if message.get("code") == Q_KEYGEN:
                self._recv_keygen(message["sender"])
            elif message.get("code") == MESSAGE:
                self.q_logger("Incoming message from {}".format(message["sender"]))
                with bb84.get_CQCConnection(self.node_name) as rx:
                    body = rx.recvClassical()
                self._recv_message(message["sender"], body)

        except Exception as e:
            self.q_logger("Exception: {}".format(e))
            _log.debug(e)

    def exit(self):
        # TODO figure out how the hell to close this...
        self.listen= False
        self.join()
