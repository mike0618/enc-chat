import socket
from pickle import dumps
import threading
from datetime import datetime
from time import sleep
from rsa import newkeys
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
    msg = f"{datetime.now().strftime('%m/%d %H:%M')}: {nickname} left the chat!\n"
    broadcast({"sender": "Enc Chat", "content": msg})


def get_data(client):
    try:
        data = rsa_decr(client.recv(1024), priv_key)
        return data
    except ConnectionResetError as e:
        print(e)
    # except:
    #     print("Something went wrong")


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
                dest[0].send(
                    message(
                        {"sender": nickname, "content": data["content"]},
                        dest[1],
                        "personal",
                    )
                )
            case "bye":
                close_client(nickname)
                break
        # try:
        #     message = client.recv(1024).decode()
        #     if not message:
        #         close_client(nickname)
        #         break
        #     elif "@" in message and message.split("@")[0] in clients.keys():
        #         msg_data = message.split("@")
        #         receiver = clients.get(msg_data[0])
        #         if not receiver:
        #             continue
        #         msg = f"@{msg_data[0]}:{nickname}: {msg_data[1]}\n".encode()
        #         receiver.send(msg)
        #         client.send(msg)
        #     elif message.startswith("/"):
        #         msg_data = message.split("@")
        #         if len(msg_data) < 2:
        #             continue
        #         receiver = clients.get(msg_data[1])
        #         if not receiver:
        #             continue
        #         receiver.send(f"{msg_data[0]}@{nickname}".encode())
        #     else:
        #         message = f"{nickname}: {message}\n"
        #         broadcast(message.encode())
        # except:
        #     close_client(nickname)
        #     break


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
        data = get_data(client)
        if not data:
            continue
        if data["type"] == "NICK":
            nickname = data["content"]["nickname"]
            client_key = data["content"]["pub_key"]
        if not nickname:
            continue
        print(f"Nickname of the client is {nickname}!")
        clients[nickname] = (client, client_key)
        msg = f"{datetime.now().strftime('%m/%d %H:%M')}: {nickname} joined the chat!\n"
        broadcast({"sender": "Enc Chat", "content": msg})
        sleep(0.2)
        send_users()
        print(f"Users list sended to {nickname}")

        thread = threading.Thread(target=handle, args=(nickname,))
        thread.start()


if __name__ == "__main__":
    print(f"Server is listening at {host}:{port}")
    receive()
