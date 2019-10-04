import npyscreen


###############################################
# TUI prototype
###############################################
class App(npyscreen.StandardApp):
    def onStart(self):
        app_name = "bbchat"
        self.main = self.addForm("MAIN", MainForm, name=app_name)

    def add_q_log(self, entry):
        self.main.quantum_log.append(str(entry))
        # self.quantum_status.values = self.quantum_log
        self.main.quantum_status.display()

    def add_message(self, entry):
        self.main.message_store.append(entry)
        self.main.message_viewer.values = self.main.message_store
        self.main.message_viewer.display()


class MessageInput(npyscreen.BoxTitle):
    _contained_widget = npyscreen.MultiLineEdit


class MainForm(npyscreen.FormBaseNew):
    message_store = ["Message 1", "Message 2"]
    quantum_log = []
    # constructor
    def create(self):
        y, x = self.useable_space()
        new_handlers = {"^Q": self.exit_func}
        self.add_handlers(new_handlers)

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
            values=self.message_store,
            max_height=2 * y // 3,
            max_width=2 * x // 3 - 4,
            rely=2,
            relx=2,
        )

    def exit_func(self, _input):
        exit(0)


MyApp = App()
MyApp.run()
for i in range(10):
    self.add_message("Message {}".format(i))
