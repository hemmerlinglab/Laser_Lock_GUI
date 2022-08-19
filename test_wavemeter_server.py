import socket

def init_wavemeter():

    # Create a TCP/IP socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    # Connect the socket to the port where the server is listening
    #server_address = ('localhost', 10000)
    server_address = ('192.168.42.20', 62500)
    print('connecting to %s port %s' % server_address)
    sock.connect(server_address)

    return sock

def get_frequencies(sock):

    ## Create a TCP/IP socket
    #sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    ## Connect the socket to the port where the server is listening
    ##server_address = ('localhost', 10000)
    #server_address = ('192.168.42.20', 62500)
    #print('connecting to %s port %s' % server_address)
    #sock.connect(server_address)

    #if True:
    try:
    
        # Send data
        message = 'request'
        print('sending "%s"' % message)
        sock.sendall(message.encode())

        # Look for the response
        amount_received = 0
        amount_expected = len(message)
    
        while amount_received < amount_expected:
            data = sock.recv(21)
            amount_received += len(data)
            print('received "%s"' % data)

        data = data.decode().split(',')
        data = list(map(float,data))

    finally:
    #except:
        print('closing socket')
        sock.close()

    return data




while True:

    sock = init_wavemeter()
    
    v = get_frequencies(sock)

    print(v)


#sock.close()

