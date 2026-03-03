import socket

HOST = "192.168.42.26"
PORT = 63700
MAX_CAPACITY = 1

# AF_INET means ipv4, SOCK_STREAM means TCP
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.bind((HOST, PORT))
sock.listen(MAX_CAPACITY)

print(f"Host is listening, IP = {HOST}, Port = {PORT} ...")

# This command will make the socket wait for connection forever, until some clients is reaching out
connection, client_addr = sock.accept()

with connection:
    print(f"received connection from {client_addr}")

    # This code below enables us to read a line ended by \n or \r\n, even though "file" appears here, it does not involve any file IO. readline would also automatically decode the received message
    with connection.makefile('r', encoding='utf-8', newline='') as rf:
        while True:
            data = rf.readline().rstrip('\r\n')

            if not data: break

            try:
                parsed_msg = data.split(',')
                laserid = parsed_msg[0]
                if parsed_msg[1] == '?':
                    print(f"Get task to return last value of measured {laserid} frequency!")
                    connection.sendall("422,709.078380\n".encode())
                else:
                    setpoint = float(parsed_msg[1])
                    print(f"Laserid: {laserid}, Setpoint: {setpoint}")
                    connection.sendall(b'1\n')

            except (ValueError, IndexError):
                print(f"Failed to parse message: {data!r}")
                connection.sendall(b'0\n')

print("client has closed the connection.")

"""
For the actual program in `laser_gui_BI871.py`, it requires
message format to be:
    f"{laserid,setpoint}", e.g. "422,709.07824"
"""
