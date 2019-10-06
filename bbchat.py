import sys
import getopt
import npyscreen
import curses

from bbclient import *


class BBChat(npyscreen.StandardApp):
    message_store = []

    def configure(self, initiator=True, client=None, key_length=32):
        self.initiator = initiator

        if initiator:
            self.name = "Alice"
            self.recipient = "Bob"
        else:
            self.name = "Bob"
            self.recipient = "Alice"
        self.client = client
        if self.client is None:
            self.client = Client(initiator, key_length, q_logger=self.add_q_log)

    def onStart(self):
        # Start TUI
        app_name = "bbchat"
        self.tui = self.addForm("MAIN", MainForm, name=app_name)
        # In case I want to display an initial message
        self.tui.set_messages(self.message_store)
        self.initialize_handers()

    def initialize_handers(self):
        new_handlers = {
            "^Q": self.exit_func,
            curses.ascii.alt(curses.ascii.NL): self.send_message,
        }
        self.tui.add_handlers(new_handlers)

    def add_q_log(self, entry):
        self.tui.quantum_log.append(str(entry))
        self.tui.quantum_status.values = self.tui.quantum_log
        self.tui.quantum_status.display()

    def add_message(self, entry):
        self.message_store.append(entry)
        self.tui.set_messages(self.message_store)

    def send_message(self, some_value):
        # Update view
        m = self.tui.input.value
        self.tui.input.value = ""
        self.add_message(("me", m))

        # Send message to remote user
        self.client.send_message(self.recipient, m)

    def exit_func(self, _input):
        exit(0)


class MessageInput(npyscreen.BoxTitle):
    _contained_widget = npyscreen.MultiLineEdit


###############################################
# TUI prototype
###############################################
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
            npyscreen.BoxTitle,
            name="Quantum Log",
            values=self.quantum_log,
            relx=2 * x // 3,
            rely=2,
            max_width=x // 3 - 2,
        )
        self.message_viewer = self.add(
            npyscreen.BoxTitle,
            name="Chat",
            values=[],
            max_height=2 * y // 3,
            max_width=2 * x // 3 - 4,
            rely=2,
            relx=2,
        )

    def set_messages(self, messages):
        fmt_messages = ["{}: {}".format(i[0], i[1]) for i in messages]
        self.message_viewer.values = fmt_messages
        self.message_viewer.display()


initialize = ""
try:
    opts, args = getopt.getopt(sys.argv[1:], "i")
except getopt.GetoptError:
    pass

MyApp = BBChat()
for opt, _ in opts:
    if opt == "-i":
        MyApp.configure(initiator=True)
        MyApp.run()
    else:
        print(usage)
        sys.exit(2)
if len(opts) < 1:
    MyApp.configure(initiator=False)
    MyApp.run()
