import array
import json
import logging
import os
import queue
import select
import signal
import socket
import sys
from threading import Thread

from bb84 import bb84
from cqc.pythonLib import CQCConnection

# Com Headers
Q_KEYGEN = 5
KEYGEN_OK = 10
MESSAGE = 20

_log = logging.getLogger("BBChat")


class Client(Thread):
    key_map = {}

    def __init__(
        self,
        initiator,
        key_length,
        message_add,
        node_name="Alice",
        recipient="Bob",
        q_logger=print,
        key_generated=None,
    ):
        # For now use a key for a default recipient, "Bob"
        Thread.__init__(self)
        self.initiator = initiator

        # Yeah.. if we would get rid of this code at some point, that'd be great..
        self.recipient = recipient

        self.key_length = key_length
        self.node_name = node_name
        self.q_logger = q_logger
        self.message_add = message_add
        self.msg_queue = queue.Queue()
        self.conn = None
        self.listening = True
        self.key_generated = key_generated

    def run(self):
        # Generate key
        try:
            if self.initiator:
                self._initiate_keygen(self.recipient)
            else:
                self._recv_keygen(self.recipient)

            if self.key_generated != None:
                self.key_generated(int(self.key_map[self.recipient]))

            # With the key generated, connect to peer
            port = 7070
            # Get connection to recipient
            if self.initiator:
                self.start_rx(port)
                # self.start_tx(cqc, 8081)
            else:
                self.start_tx(port)
                # self.start_rx(cqc, 8080)

            self.q_logger("Listening")
            # main loop
            while self.listening:
                self._check_messages()
        except Exception as e:
            self.message_add(("err", e))

    def start_rx(self, port):
        """
        self.rx = None
        self.info("Opening socket")
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.info("Biniding socket")
        sock.bind(("", port))
        self.info("Accepting connection")

        sock.listen(1)
        while self.rx is None:
            self.info("Trying to accept connection: ({}, {})".format("", port))
            (self.rx, addr) = sock.accept()
        self.info("Connected to {}".format(addr))
        """
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1)
        s.bind(("", port))
        s.listen(1)
        while self.conn is None and self.listening:
            (self.conn, addr) = s.accept()
        self.info("Connected to {}".format(addr))

    def start_tx(self, port):
        attempts = 10
        self.info("Opening socket")
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.info("Connecting")
        self.info("Trying to connect to ({}, {})".format("", port))
        for i in range(attempts):
            try:
                self.conn.connect(("", port))
            except:

                if i < attempts:
                    self.q_logger("Trying again")
                else:
                    self.q_logger("Connection rejected")
                    self.exit()

    def info(self, msg):
        self.message_add(("INFO", msg))

    def _initiate_keygen(self, recipient):
        init_msg = {"code": Q_KEYGEN, "sender": self.node_name}
        # with bb84.get_CQCConnection(self.node_name) as cqc:
        # cqc.sendClassical(recipient, json.dumps(init_msg).encode())
        try:
            k = bb84.initiate_keygen(
                name=self.node_name,
                recipient=recipient,
                q_logger=self.q_logger,
                key_size=self.key_length,
            )
            self.info("storing key")
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
            self.info("storing key")
            self.key_map[initiator] = k
        except bb84.PoorErrorRate as e:
            self.q_logger("Bad error rate. Attempting again")
            self._recv_keygen(initiator)

    def send_message(self, recipient, message):
        # self.msg_queue.put({"recipient": recipient, "body": message})
        self.msg_queue.put(message)

    def _send_message(self, message):
        key = self.key_map[self.recipient]
        # packet = json.dumps({"code": MESSAGE, "sender": self.node_name})

        self.q_logger("Encrypting message")
        try:
            encrypted = bb84.encrypt(message, int(key))
        except Exception as e:
            self.info("Error encrypting: {}".format(e))
            return

        self.q_logger("Transmitting message")
        # cqc.sendClassical(recipient, bytearray(packet, "utf-8"))
        self.q_logger("Header sent")
        self.conn.send(bytes(encrypted))
        self.q_logger("Message sent")

    def _recv_message(self, body):
        sender = self.recipient
        key = self.key_map[sender]
        message = bb84.decrypt(body, int(key))
        self.message_add((sender, message.decode("utf-8")))

    def _check_messages(self):
        try:
            # Check for messages
            rx_ready, tx_ready, _ = select.select([self.conn], [self.conn], [], 1)

            for rx in rx_ready:
                raw = self.conn.recv(1024)
                if len(raw) > 0:
                    self._recv_message(raw)

            for tx in tx_ready:
                while not self.msg_queue.empty():
                    msg = self.msg_queue.get()
                    self._send_message(msg)
                # self.message_add(("rx: ", self.conn.recv(1024)))

        except Exception as e:
            self.info("Exception: {}".format(e))
            self.info("Listener stopped")
            self.exit()

            # _log.debug(e)

    def exit(self):
        # TODO figure out how the hell to close this...
        self.listening = False
        if not self.conn is None:
            self.conn.close()
        # os.kill(self.ident, signal.SIGTERM)
