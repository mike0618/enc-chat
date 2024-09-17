import socket
import json
import threading
from datetime import datetime
import rsa

host = socket.gethostbyname(socket.gethostname())
port = 16180
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()
pub_key, priv_key = rsa.newkeys(1024)

clients = {}


def send_users():
    nick_ips = {nick: client.getpeername() for nick, client in clients.items()}
    broadcast(bytes(json.dumps(nick_ips), encoding="UTF-8"))


def broadcast(message):
    for client in clients.values():
        # if client.getpeername() == ip:
        # continue
        client.send(message)


def close_client(nickname):
    if nickname not in clients:
        return False
    client = clients[nickname]
    client.close()
    clients.pop(nickname)
    send_users()
    broadcast(
        f"{datetime.now().strftime('%m/%d %H:%M')}: {nickname} left the chat!\n".encode(
            "UTF-8"
        )
    )


def handle(nickname):
    if not nickname:
        return False
    client = clients[nickname]
    while True:
        try:
            message = client.recv(1024).decode()
            if not message:
                close_client(nickname)
                break
            elif "@" in message and message.split("@")[0] in clients.keys():
                msg_data = message.split("@")
                receiver = clients.get(msg_data[0])
                if not receiver:
                    continue
                msg = f"@{msg_data[0]}:{nickname}: {msg_data[1]}\n".encode()
                receiver.send(msg)
                client.send(msg)
            elif message.startswith("/"):
                msg_data = message.split("@")
                if len(msg_data) < 2:
                    continue
                receiver = clients.get(msg_data[1])
                if not receiver:
                    continue
                receiver.send(f"{msg_data[0]}@{nickname}".encode())
            else:
                message = f"{nickname}: {message}\n"
                broadcast(message.encode())
        except:
            close_client(nickname)
            break


def receive():
    while True:
        try:
            client, address = server.accept()
        except KeyboardInterrupt:
            break
        print(f"Connected with {str(address)}")
        client.send("NICK".encode("UTF-8"))
        try:
            nickname = client.recv(1024).decode("UTF-8")
        except ConnectionResetError:
            continue
        if not nickname:
            continue

        print(f"Nickname of the client is {nickname}!")
        client.send("Connected to the server!\n".encode("UTF-8"))
        broadcast(
            f"{datetime.now().strftime('%m/%d %H:%M')}: {nickname} joined the chat!\n".encode(
                "UTF-8"
            )
        )
        clients[nickname] = client
        send_users()

        thread = threading.Thread(target=handle, args=(nickname,))
        thread.start()


if __name__ == "__main__":
    print(f"Server is listening at {host}:{port}")
    receive()
