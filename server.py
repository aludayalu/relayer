import socket, json
import uuid, threading
server=socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server.bind(("0.0.0.0", 7777))
server.listen()

clientrelayer_ip="127.0.0.1"
forwardto_client: socket.socket=None
connections={}
forwarding_clients={}

queue_lock=threading.Lock()

def further_forwarder(client: socket.socket, id):

    while True:
        try:
            data=client.recv(14680064)
            if len(data)==0:
                raise Exception("client disconnected")
        except:
            try:
                client.close()
            except:
                pass
            try:
                del connections[id]
            except:
                pass
            try:
                reliable_send(forwardto_client, json.dumps({"type":"connection_close", "id":connection_id}).encode())
            except:
                pass
            return
        try:
            reliable_send(forwardto_client, json.dumps({"type":"forward_data", "id":id, "hex_data":data.hex()}).encode())
        except:
            return

def back_forwarder():
    global forwardto_client
    while True:
        try:
            message=reliable_read(forwardto_client)
        except:
            forwardto_client=None
            for x in list(connections.values()):
                try:
                    x.close()
                except:
                    pass
            connections.clear()
            return
        message=json.loads(message.decode())
        if message["type"]=="forward_data":
            try:
                connections[message["id"]].send(bytes.fromhex(message["hex_data"]))
            except:
                try:
                    del connections[message["id"]]
                except:
                    pass
                try:
                    reliable_send(forwardto_client, json.dumps({"type":"connection_close", "id":message["id"]}).encode())
                except:
                    pass
        elif message["type"]=="connection_close":
            try:
                connections[message["id"]].close()
            except:
                pass
            try:
                del connections[message["id"]]
            except:
                pass

def reliable_send(client, message: bytes):
    global forwardto_client
    message_length_in_bytes=len(message).to_bytes(16, "little", signed=False)
    queue_lock.acquire()
    try:
        client.send(message_length_in_bytes+message)
        queue_lock.release()
    except Exception as e:
        queue_lock.release()
        import traceback
        traceback.print_exc()
        forwardto_client=None
        for x in list(connections.values()):
            try:
                x.close()
            except:
                pass
        connections.clear()
        raise e

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

def reliable_read(client):
    message_length=int.from_bytes(recv_n_bytes(client, 16), "little", signed=False)
    message=recv_n_bytes(client, message_length)
    return message

while True:
    client, addr=server.accept()
    if addr[0]==clientrelayer_ip and (forwardto_client==None):
        forwardto_client=client
        threading.Thread(target=back_forwarder).start()
        print("forwarding receiver client connected")
    else:
        if forwardto_client==None:
            client.close()
        else:
            connection_id=uuid.uuid4().__str__()
            connections[connection_id]=client
            reliable_send(forwardto_client, json.dumps({"type":"connection_new", "id":connection_id}).encode())
            threading.Thread(target=further_forwarder, args=(client, connection_id)).start()