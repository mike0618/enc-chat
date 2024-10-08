import socket
from pickle import loads
from os import _exit
from time import sleep
from threading import Thread
import tkinter.scrolledtext
from tkinter import simpledialog, messagebox, END, Label, Button, Text, Tk
from rsa import DecryptionError, newkeys
from mycrypt import rsa_enc, rsa_decr

pub_key, priv_key = newkeys(1024)


class GUI:
    def __init__(self) -> None:
        self.nickname = None
        self.host = "140.228.209.20"
        # self.host = socket.gethostbyname(socket.gethostname())
        self.port = 16180
        self.client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.client.settimeout(3)
        self.authorized = False
        try:
            self.client.connect((self.host, self.port))
        except socket.timeout:
            print("Timeout")
            messagebox.showerror(title="Timeout error", message="Check your connection")
            _exit(1)
        except ConnectionRefusedError:
            messagebox.showerror(
                title="Connection refused", message="Server is not running"
            )
            _exit(1)
        self.client.settimeout(None)
        self.user = "Public"
        self.user_key = None
        self.server_key = pub_key
        self.users = {"Public": ""}
        self.counts = {"Public": 0}
        self.messages = {"Public": []}

    def send_nick(self, msg="Enter a nickname"):
        w = Tk()  # tmp parent tkinter workaround
        w.withdraw()
        self.win.withdraw()
        self.nickname = simpledialog.askstring("EncChat: Connected", msg, parent=w)
        w.destroy()
        self.win.deiconify()
        msg = {"nickname": self.nickname, "pub_key": pub_key}
        self.client.send(self.message(msg, "NICK"))

    def gui_loop(self):
        self.win = Tk()
        self.win.title("Enc Chat")
        self.win.resizable(False, False)
        self.win.configure(bg="lightgray")

        self.title_lbl = Label(self.win, text="", bg="lightgray")
        self.title_lbl.config(font=("Arial", 12))
        self.title_lbl.grid(row=0, column=0, sticky="w")

        self.close_btn = Button(self.win, text="Close", command=self.stop)
        self.close_btn.config(font=("Arial", 12), bg="indianred")
        self.close_btn.grid(row=0, column=1, sticky="we")

        self.chat_lbl = Label(self.win, text="Chat with Public:", bg="lightgray")
        self.chat_lbl.config(font=("Arial", 12))
        self.chat_lbl.grid(row=1, column=0, sticky="w")

        self.users_lbl = Label(self.win, text="Users:", bg="lightgray")
        self.users_lbl.config(font=("Arial", 12))
        self.users_lbl.grid(row=1, column=1, sticky="w")

        self.text_area = tkinter.scrolledtext.ScrolledText(self.win)
        self.text_area.config(font=("Arial", 12), state="disabled", width=55, height=10)
        self.text_area.grid(row=2, column=0, sticky="ew")

        self.msg_lbl = Label(self.win, text="Message:", bg="lightgray")
        self.msg_lbl.config(font=("Arial", 12))
        self.msg_lbl.grid(row=3, column=0, sticky="w")

        self.input_area = Text(self.win, height=3)
        self.input_area.config(font=("Arial", 12), width=55)
        self.input_area.grid(row=4, column=0, sticky="we")
        self.input_area.focus()
        self.input_area.bind("<Shift-Return>", lambda event: self.send_msg())

        self.send_btn = Button(self.win, text="✉", command=self.send_msg)
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
        self.text_area.delete("1.0", END)
        messages = self.messages.get(self.user)
        if messages:
            for m in messages:
                self.text_area.insert(END, m)
        self.counts[self.user] = 0
        self.upd_user_lst()
        self.text_area.yview(END)
        self.text_area.config(state="disabled")
        self.chat_lbl.configure(text=f"Chat with {self.user}:")
        self.user_lst.itemconfig(select[0], fg="white", bg="black")

    def message(self, content, msg_type="public", pubkey=None, dest="public"):
        if pubkey:
            content = rsa_enc(content, pubkey)
        return rsa_enc(
            {"type": msg_type, "dest": dest, "content": content}, self.server_key
        )

    def receive(self):
        while True:
            try:
                data = self.client.recv(1024)
            except InterruptedError:
                print("An error occured!")
                self.client.close()
                self.stop()
            except ConnectionResetError:
                self.stop()
            try:
                data = rsa_decr(data, priv_key)
            except DecryptionError:
                if not data:
                    continue
                data = loads(data)
                if data["type"] == "NICK" and not self.authorized:
                    # allow only first NICK request for security, to prevent unencrypted control
                    self.authorized = True
                    self.server_key = data["content"]
                    self.send_nick()
                continue  # it is important here
            except EOFError:
                self.stop()
            if not data:
                return False
            msg_type = data["type"]
            message = data["content"]
            if not message:
                return False
            match msg_type:
                case "chnick":
                    msg = f"The nickname {self.nickname} occupied!\nEnter another nickname:"
                    self.send_nick(msg)
                case "users":
                    self.users = {"Public": ""}
                    self.users.update(message)
                    self.upd_user_lst()
                    if self.user not in self.users:
                        self.user = "Public"
                        self.chat_lbl.config(text="Chat with Public")
                    if not self.title_lbl.cget("text"):
                        self.title_lbl.config(text=f"Enc Chat: Welcome {self.nickname}")
                case "personal":
                    msg = rsa_decr(message["content"], priv_key)
                    sender = message["sender"]
                    msg = f"{sender}:\n{msg}\n\n"
                    self.add_msg(sender, msg)
                case "public":
                    msg = message["content"]
                    sender = message["sender"]
                    msg = f"{sender}:\n{msg}\n\n"
                    self.add_msg("Public", msg)

    def upd_user_lst(self):
        self.user_lst.delete(0, END)
        for i, nick in enumerate(self.users):
            cnt = self.counts.get(nick)
            if not cnt:
                cnt = ""
            else:
                cnt = f"- {cnt} ✉"
            self.user_lst.insert(END, f"{nick} {cnt}")
            if self.user == nick and self.user in self.users:
                self.user_lst.itemconfig(i, fg="white", bg="black")
        if self.user not in self.users:
            self.user_lst.itemconfig(0, fg="white", bg="black")

    def add_msg(self, usr, msg):
        self.messages.setdefault(usr, [])
        self.messages[usr].append(msg)
        if usr == self.user:
            self.text_area.config(state="normal")
            self.text_area.insert(END, msg)
            self.text_area.yview(END)
            self.text_area.config(state="disabled")
        else:
            self.counts.setdefault(usr, 0)
            self.counts[usr] += 1
            self.upd_user_lst()

    def send_msg(self):
        msg = self.input_area.get("1.0", END).strip()
        self.input_area.delete("1.0", END)
        if not msg:
            return False
        if self.user == "Public":
            self.client.send(self.message(msg))
        else:
            self.client.send(
                self.message(msg, "personal", self.users[self.user], self.user)
            )
            self.add_msg(self.user, f"{self.nickname}:\n{msg}\n\n")

    def stop(self):
        self.win.destroy()
        self.win.quit()
        if self.client:
            self.client.send(self.message("", "bye"))
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


if __name__ == "__main__":
    main()
