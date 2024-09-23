import socket
from pickle import dumps
import threading
from datetime import datetime
from time import sleep
from rsa import DecryptionError, newkeys
from mycrypt import rsa_decr, rsa_enc

host = socket.gethostbyname(socket.gethostname())
port = 16180
server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind((host, port))
server.listen()
pub_key, priv_key = newkeys(1024)

clients = {}


def message(content, pubkey, msg_type="public"):
    return rsa_enc({"type": msg_type, "content": content}, pubkey)


def send_users():
    users = {nick: client[1] for nick, client in clients.items()}
    broadcast(users, "users")


def broadcast(msg, msg_type="public"):
    [client[0].send(message(msg, client[1], msg_type)) for client in clients.values()]


def close_client(nickname):
    if nickname not in clients:
        return False
    client = clients[nickname][0]
    print(f"bye, {nickname}")
    client.close()
    clients.pop(nickname)
    send_users()
    msg = f"{datetime.now().strftime('%m/%d %H:%M')}: {nickname} left the chat!"
    broadcast({"sender": "Enc Chat", "content": msg})


def get_data(client):
    try:
        return rsa_decr(client.recv(1024), priv_key)
    except ConnectionResetError as e:
        print(e)
    except DecryptionError:
        print(f"DecryptionError: {client}")


def handle(nickname):
    if not nickname:
        return False
    client = clients[nickname][0]
    while True:
        data = get_data(client)
        if not data:
            close_client(nickname)
            break
        match data["type"]:
            case "public":
                broadcast({"sender": nickname, "content": data["content"]})
            case "personal":
                dest = clients[data["dest"]]
                msg = {"sender": nickname, "content": data["content"]}
                dest[0].send(message(msg, dest[1], "personal"))
            case "bye":
                close_client(nickname)
                break


def get_nick(client):
    data = get_data(client)
    if not data or data.get("type") != "NICK":
        return False, False
    nickname = data["content"]["nickname"]
    client_key = data["content"]["pub_key"]
    print(f"Nickname of the client is {nickname}!")
    return nickname, client_key


def receive():
    nickname = None
    client_key = None
    while True:
        try:
            client, address = server.accept()
        except KeyboardInterrupt:
            break
        print(f"Connected with {str(address)}")
        client.send(dumps({"type": "NICK", "content": pub_key}))
        nickname, client_key = get_nick(client)
        while nickname in clients:
            client.send(message("chnick", client_key, "chnick"))
            nickname, client_key = get_nick(client)
            if not nickname or not client_key:
                client.close()
                break
        if not nickname or not client_key:
            continue
        clients[nickname] = (client, client_key)
        msg = f"{datetime.now().strftime('%m/%d %H:%M')}: {nickname} joined the chat!"
        broadcast({"sender": "Enc Chat", "content": msg})
        sleep(0.2)
        send_users()

        thread = threading.Thread(target=handle, args=(nickname,))
        thread.start()


if __name__ == "__main__":
    print(f"Server is listening at {host}:{port}")
    receive()
