import socket, json
import uuid, threading

server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.connect(("127.0.0.1", 7777))

connections={}
exposing_server=("127.0.0.1", 25565)

def reliable_send(client, message: bytes):
    message_length_in_bytes=len(message).to_bytes(4, "little", signed=False)
    try:
        client.send(message_length_in_bytes+message)
    except Exception as e:
        raise e

def reliable_read(client):
    message_length=int.from_bytes(recv_n_bytes(client, 4), "little", signed=False)
    message=recv_n_bytes(client, message_length)
    return message

def recv_n_bytes(client, n) -> bytes:
    data=b""
    left_to_read=n
    while True:
        temp=client.recv(left_to_read)
        if len(temp)==0:
            raise Exception("client disconnected")
        left_to_read=left_to_read-len(temp)
        data+=temp
        if left_to_read==0:
            break
    return data

def local_connection_thread(local_connection: socket.socket, id):
    while True:
        try:
            data=local_connection.recv(14680064)
            if len(data)==0:
                raise Exception("client disconnected")
        except:
            try:
                reliable_send(server, json.dumps({"type":"connection_close", "id":id}).encode())
            except:
                pass
            try:
                del connections[id]
            except:
                pass
            return
        reliable_send(server, json.dumps({"type":"forward_data", "id":id, "hex_data": data.hex()}).encode())

while True:
    message=json.loads(reliable_read(server).decode())
    if message["type"]=="connection_new":
        client=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect(exposing_server)
        connections[message["id"]]=client
        threading.Thread(target=local_connection_thread, args=(client, message["id"])).start()
    if message["type"]=="connection_close":
        try:
            connections[message["id"]].close()
        except:
            pass
        try:
            del connections[message["id"]]
        except:
            pass
    if message["type"]=="forward_data":
        try:
            connections[message["id"]].send(bytes.fromhex(message["hex_data"]))
        except:
            try:
                del connections[message["id"]]
            except:
                pass
            reliable_send(server, json.dumps({"type":"connection_close", "id":message["id"]}).encode())