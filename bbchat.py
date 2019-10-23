import sys
import signal
import getopt
import npyscreen
import curses
import logging

from bbclient import *
import config as bbConfig

_log = logging.getLogger("BBChat")


class BBChat(npyscreen.StandardApp):
    message_store = []
    quantum_log = []
    mode = "KEYGEN"

    def configure(
        self,
        initiator=True,
        client=None,
        key_length=32,
        eavesdropping=None,
        eavesdropper=False,
    ):
        _log.debug("configuring chat object")
        self.initiator = initiator
        self.key_length = key_length

        if initiator:
            self.name = "Alice"
            self.recipient = "Bob"
        else:
            self.name = "Bob"
            self.recipient = "Bob"

        # If we're using an evesdropper redirect communication
        if eavesdropper:
            self.recipient = "Eve"

        self.client = client

    def onStart(self):
        # Start TUI
        app_name = "bbchat"
        self.qv = self.addForm("MAIN", QuantumViewer, name=app_name)
        self.tui = self.addForm("CHAT", MainForm, name=app_name)
        self.view = self.qv

        # In case I want to display an initial message
        self.tui.set_messages(self.message_store)
        self.initialize_handers()
        if self.client is None:
            self.client = Client(
                self.initiator,
                self.key_length,
                self.add_message,
                q_logger=self.add_q_log,
                node_name=self.name,
                recipient=self.recipient,
            )
        self.client.start()

    def chat(self, _):
        self.view.editing = False
        self.switchForm("CHAT")
        self.view = self.tui
        q_log = self.quantum_log
        self.quantum_log = []
        for l in q_log:
            self.add_q_log(l)

    def initialize_handers(self):
        signal.signal(signal.SIGTERM, self.exit_func)
        signal.signal(signal.SIGINT, self.exit_func)

        tui_handlers = {
            "^Q": self.exit_func,
            curses.ascii.alt(curses.ascii.NL): self.send_message,
        }
        self.tui.add_handlers(tui_handlers)

        q_log_handlers = {curses.ascii.alt(curses.ascii.NL): self.chat}
        self.qv.add_handlers(q_log_handlers)

    def add_q_log(self, entry):
        msg = str(entry)
        width = self.view.quantum_status.width - 7
        for i in range(0, len(msg), width):
            end = i + width

            if i + width > len(msg):
                end = len(msg)

            self.quantum_log = [msg[i:end]] + self.quantum_log
        # Update the appropriate form
        self.view.quantum_status.values = self.quantum_log
        self.view.quantum_status.display()

    def add_message(self, entry):
        # Add message sender
        # Slice messages by width and add them to the message store
        msg = str(entry[1])
        width = self.tui.message_viewer.width - 7
        message_parts = []
        for i in range(0, len(msg), width):
            end = i + width

            if i + width > len(msg):
                end = len(msg)

            message_parts.append("  " + msg[i:end])

        self.message_store = message_parts + self.message_store
        self.message_store = [entry[0] + ":"] + self.message_store
        self.view.set_messages(self.message_store)

    def send_message(self, _):
        # Update view
        msg = self.tui.input.value

        if msg == "":
            return

        self.tui.input.value = ""
        self.add_message(("me", msg))

        # Send message to remote user
        self.client.send_message(self.recipient, msg)

    def exit_func(self, *args):
        print("Killing listener")
        self.client.exit()
        self.client.join()
        exit(0)


class MessageInput(npyscreen.BoxTitle):
    _contained_widget = npyscreen.MultiLineEdit


class Viewer(npyscreen.BoxTitle):
    _contained_widget = npyscreen.Pager


###############################################
# TUI prototype
###############################################
class QuantumViewer(npyscreen.FormBaseNew):
    quantum_log = []

    # constructor
    def create(self):
        self.quantum_status = self.add(npyscreen.Pager, values=self.quantum_log)

    def set_messages(self, messages):
        self.quantum_status.values = messages + self.quantum_status.values


class MainForm(npyscreen.FormBaseNew):
    quantum_log = []

    # constructor
    def create(self):
        y, x = self.useable_space()

        self.input = self.add(
            MessageInput,
            name="Write a message",
            max_width=2 * x // 3 - 4,
            rely=(2 * y // 3) + 2,
            relx=2,
        )
        self.quantum_status = self.add(
            Viewer,
            name="Quantum Log",
            values=self.quantum_log,
            relx=2 * x // 3,
            rely=2,
            max_width=x // 3 - 2,
            editable=False,
        )
        self.message_viewer = self.add(
            Viewer,
            name="Chat",
            values=[],
            max_height=2 * y // 3,
            max_width=2 * x // 3 - 4,
            rely=2,
            relx=2,
            editable=False,
        )

    def set_messages(self, messages):
        # fmt_messages = ["{}: {}".format(i[0], i[1]) for i in messages]
        self.message_viewer.values = messages
        self.message_viewer.update()


initialize = ""
opts = None
try:
    opts, args = getopt.getopt(sys.argv[1:], "ie", ["eavesdrop"])
except getopt.GetoptError:
    pass

bbConfig.config()
myapp = BBChat()
kwargs = {"initiator": False, "eavesdropping": False, "eavesdropper": False}
try:
    for opt, arg in opts:
        if opt == "-i":
            kwargs["initiator"] = True
        elif opt == "-e":
            kwargs["eavesdropper"] = True
        elif opt == "--eavesdropp":
            kwargs["eavesdropping"] = True
        else:
            print(usage)
            sys.exit(2)
    myapp.configure(**kwargs)
    myapp.run()
except Exception as e:
    print(e)
    myapp.exit_func()
    _log.debug(e)
