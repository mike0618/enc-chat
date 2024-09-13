import socket
import json
from os import _exit, path
from time import sleep
from threading import Thread
import tkinter
import tkinter.scrolledtext
from tkinter import simpledialog, messagebox

cwd = path.dirname(path.realpath(__file__))
msg = tkinter.Tk()
msg.withdraw()
nickname = simpledialog.askstring("Nickname", "Enter a nickname", parent=msg)


class GUI:
    def __init__(self) -> None:
        # self.host = "192.168.1.67"
        self.host = socket.gethostbyname(socket.gethostname())
        self.port = 16180
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(3)
        try:
            self.client.connect((self.host, self.port))
        except socket.timeout:
            print("Timeout")
            messagebox.showerror(
                title="Timeout error", message="Check your VPN connection"
            )
            _exit(1)
        except ConnectionRefusedError:
            messagebox.showerror(
                title="Connection refused", message="Server is not running"
            )
            _exit(1)
        self.client.settimeout(None)
        self.user = "All"
        self.users = {"All": ""}
        self.counts = {"All": 0}
        self.messages = {"All": []}

    def gui_loop(self):
        self.win = tkinter.Tk()
        self.win.title("Enc Chat")
        self.win.resizable(False, False)
        self.win.configure(bg="lightgray")

        self.title_lbl = tkinter.Label(self.win, text="", bg="lightgray")
        self.title_lbl.config(font=("Arial", 12))
        self.title_lbl.grid(row=0, column=0, sticky="w")

        self.close_btn = tkinter.Button(self.win, text="Close", command=self.stop)
        self.close_btn.config(font=("Arial", 12), bg="indianred")
        self.close_btn.grid(row=0, column=1, sticky="we")

        self.chat_lbl = tkinter.Label(self.win, text="Chat with All:", bg="lightgray")
        self.chat_lbl.config(font=("Arial", 12))
        self.chat_lbl.grid(row=1, column=0, sticky="w")

        self.users_lbl = tkinter.Label(self.win, text="Users:", bg="lightgray")
        self.users_lbl.config(font=("Arial", 12))
        self.users_lbl.grid(row=1, column=1, sticky="w")

        self.text_area = tkinter.scrolledtext.ScrolledText(self.win)
        self.text_area.config(font=("Arial", 12), state="disabled", width=55, height=10)
        self.text_area.grid(row=2, column=0, sticky="ew")

        self.msg_lbl = tkinter.Label(self.win, text="Message:", bg="lightgray")
        self.msg_lbl.config(font=("Arial", 12))
        self.msg_lbl.grid(row=3, column=0, sticky="w")

        self.input_area = tkinter.Text(self.win, height=3)
        self.input_area.config(font=("Arial", 12), width=55)
        self.input_area.grid(row=4, column=0, sticky="we")
        self.input_area.focus()
        self.input_area.bind("<Shift-Return>", self.key_handler)

        self.send_btn = tkinter.Button(self.win, text="✉", command=self.get_msg)
        self.send_btn.config(font=("Arial", 32), bg="lightgreen")
        self.send_btn.grid(row=4, column=1, sticky="nsew")

        self.user_lst = tkinter.Listbox(self.win, activestyle="none")
        self.user_lst.config(font=("Arial", 12))
        self.user_lst.grid(row=2, column=1, sticky="ne")
        self.user_lst.bind("<<ListboxSelect>>", self.on_user_list)

        self.win.protocol("WM_DELETE_WINDOW", self.stop)
        self.win.mainloop()

    def on_user_list(self, event):
        select = event.widget.curselection()
        if not select:
            return False
        self.user = event.widget.get(select[0]).split()[0]
        self.text_area.config(state="normal")
        self.text_area.delete("1.0", "end")
        messages = self.messages.get(self.user)
        if messages:
            for m in messages:
                self.text_area.insert("end", m)
        self.counts[self.user] = 0
        self.upd_user_lst()
        self.text_area.config(state="disabled")
        self.chat_lbl.configure(text=f"Chat with {self.user}:")
        self.user_lst.itemconfig(select[0], fg="white", bg="black")

    def receive(self):
        while True:
            try:
                message = self.client.recv(1024).decode()
            except InterruptedError:
                print("An error occured!")
                self.client.close()
                return False
            if not message or not nickname:
                return False
            if message == "NICK":
                self.client.send(nickname.encode())
            elif message == "BYE":
                return True
            elif message.startswith("{"):
                self.users = {"All": ""}
                self.users.update(json.loads(message))
                self.upd_user_lst()
                if self.user not in self.users:
                    self.user = "All"
                    self.chat_lbl.config(text="Chat with All")
                if not self.title_lbl.cget("text"):
                    self.title_lbl.config(
                        text=f"Enc Chat: Welcome {nickname}, your IP is {self.users[nickname][0]}"
                    )
            elif message.startswith("@"):
                msg = message.split(":", 1)[1]
                receiver = message[1:].split(":", 1)[0]
                sender = msg.split(":")[0].strip()
                if nickname == sender:
                    self.add_msg(receiver, msg)
                else:
                    self.add_msg(sender, msg)
                if nickname == sender or self.user == sender:
                    self.write_msg(msg)
                if msg.startswith(f"{nickname}:"):
                    self.input_area.delete("1.0", "end")
            elif message.startswith("/"):
                continue
            else:
                self.messages["All"].append(message)
                if self.user == "All":
                    self.write_msg(message)
                else:
                    self.counts["All"] += 1
                    self.upd_user_lst()
                if message.startswith(f"{nickname}:"):
                    self.input_area.delete("1.0", "end")

    def upd_user_lst(self):
        self.user_lst.delete(0, "end")
        for i, nick in enumerate(self.users):
            cnt = self.counts.get(nick)
            if not cnt:
                cnt = ""
            else:
                cnt = f"- {cnt} ✉"
            self.user_lst.insert("end", f"{nick} {cnt}")
            if self.user == nick and self.user in self.users:
                self.user_lst.itemconfig(i, fg="white", bg="black")
        if self.user not in self.users:
            self.user_lst.itemconfig(0, fg="white", bg="black")

    def add_msg(self, usr, msg):
        self.messages.setdefault(usr, [])
        self.messages[usr].append(msg)
        if usr != self.user:
            self.counts.setdefault(usr, 0)
            self.counts[usr] += 1
            self.upd_user_lst()

    def write_msg(self, msg):
        self.text_area.config(state="normal")
        self.text_area.insert("end", msg)
        self.text_area.yview("end")
        self.text_area.config(state="disabled")

    def key_handler(self, event):
        self.get_msg()

    def get_msg(self):
        msg = self.input_area.get("1.0", "end").strip()
        if not msg:
            return False
        if self.user != "All":
            msg = f"{self.user}@{msg}"
        self.client.send(msg.encode())

    def stop(self):
        self.win.destroy()
        self.win.quit()
        if self.client:
            self.client.send("--".encode())
            sleep(0.5)
            self.client.close()
        _exit(1)


def main():
    gui = GUI()
    Thread(target=gui.gui_loop).start()
    while not (
        hasattr(gui, "text_area")
        and hasattr(gui, "user_lst")
        and hasattr(gui, "input_area")
    ):
        sleep(0.01)
    Thread(target=gui.receive).start()
    print("OK")


if __name__ == "__main__" and nickname:
    main()
