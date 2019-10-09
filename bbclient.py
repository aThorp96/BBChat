import sys
import array
import json
import logging
from cqc.pythonLib import CQCConnection
from threading import Thread

sys.path.append("../")
from bb84.bb84 import bb84

# Com Headers
Q_KEYGEN = 5
KEYGEN_OK = 10
C_MESSAGE = 20

_log = logging.getLogger("BBChat")


class Client:
    key_map = {}

    def __init__(self, key_length, message_add, node_name="Alice", q_logger=print):
        # For now use a key for a default recipient, "Bob"
        self.tx_classical = node_name + "t"
        self.rx_classical = node_name + "r"
        self.node_name = node_name
        self.q_logger = q_logger
        self.message_add = message_add
        # listen informs the listener thread to contiue
        # and will be used to reap the thread upon exit
        self.listen = True
        self.cqc_locked = False
        self.listener = Thread(target=self.listener)
        self.listener.start()
        # self.listener()

    def initiate_keygen(self, recipient):
        init_msg = {"code": Q_KEYGEN, "sender": self.node_name}
        with bb84.get_CQCConnection(self.node_name) as cqc:
            cqc.sendClassical(recipient, json.dumps(init_msg).encode())

        k = bb84.initiate_keygen(
            # name=self.node_name, recipient=recipient
            q_logger=self.q_logger
        )
        self.key_map[recipient] = k

    def recv_keygen(self, initiator):
        self.q_logger("Recieving keygen")
        k = bb84.target_keygen(
            # name=self.node_name, initiator=initiator,
            q_logger=self.q_logger
        )
        self.key_map[initiator] = k

    def send_message(self, recipient, message):
        # stop listening
        self.cqc_locked = True
        # Ensure we've co-generated a key
        if recipient not in self.key_map:
            self.q_logger("Initializing key")
            self.initiate_keygen(recipient)

        key = self.key_map[recipient]
        packet = json.dumps({"code": C_MESSAGE, "sender": self.node_name})

        self.q_logger("Encrypting message")
        encrypted = bb84.encrypt(message, key)

        with bb84.get_CQCConnection(self.node_name) as cqc:
            self.q_logger("Transmitting message")
            cqc.sendClassical(recipient, bytearray(packet, "utf-8"))
            self.q_logger("Header sent")
            cqc.sendClassical(recipient, encrypted)
            self.q_logger("Message sent")
        self.cqc_locked = False

    def recv_message(self, sender, body):
        key = self.key_map[sender]
        message = bb84.decrypt(body, int(key))
        self.message_add((sender, message.decode("utf-8")))

    def listener(self):
        message = None
        while self.listen:
            if not self.cqc_locked:
                try:
                    with bb84.get_CQCConnection(self.node_name) as rx:
                        self.cqc_locked = True
                        self.q_logger("Listening for request")
                        m = rx.recvClassical(timout=1).decode("utf-8")
                        self.q_logger(m)

                        message = json.loads(m)
                    self.cqc_locked = False
                    if message["code"] == Q_KEYGEN:
                        self.recv_keygen(message["sender"])
                    elif message["code"] == C_MESSAGE:
                        self.q_logger(
                            "Incoming message from {}".format(message["sender"])
                        )
                        with bb84.get_CQCConnection(self.node_name) as rx:
                            body = rx.recvClassical()
                        self.recv_message(message["sender"], body)
                except Exception as e:
                    self.cqc_locked = False
                    _log.debug(e)

    def exit(self):
        try:
            self.listen = False
            self.listener.exit()
        except Exception:
            # Thread not started
            pass
