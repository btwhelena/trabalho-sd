import socket
import threading
import time
import struct
import signal
import sys
import smart_environment_pb2 as gateway_pb2

# Configurações globais
MULTICAST_GROUP = ('224.1.1.1', 5007)
MULTICAST_PORT = 5007
TCP_PORT = 6000

class Gateway:
    def __init__(self):
        self.devices = {}  
        self.running = True
        signal.signal(signal.SIGINT, self.shutdown_gateway)

    def start_gateway(self):
        threading.Thread(target=self.listen_multicast, daemon=True).start()
        threading.Thread(target=self.start_tcp_server, daemon=True).start()
        print("[Gateway] Gateway iniciado.")

    def listen_multicast(self):
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as udp_sock:
            udp_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            udp_sock.bind(('', MULTICAST_PORT))
            mreq = struct.pack("4sl", socket.inet_aton(MULTICAST_GROUP[0]), socket.INADDR_ANY)
            udp_sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            print("[Gateway] Escutando mensagens multicast para descoberta de dispositivos...")
            while self.running:
                try:
                    data, addr = udp_sock.recvfrom(1024)
                    message = data.decode()
                    device_id, device_type, state, ip, port = message.split(',')
                    self.devices[device_id] = (ip, int(port), device_type, state)
                    print(f"[Gateway] Dispositivo registrado: {device_id} ({device_type}) no endereço {ip}:{port} com estado {state}")
                except Exception as e:
                    print(f"[Gateway] Erro na thread multicast: {e}")

    def start_tcp_server(self):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as server_sock:
            server_sock.bind(("localhost", TCP_PORT))
            server_sock.listen(5)
            print(f"[Gateway] Servidor TCP iniciado na porta {TCP_PORT}.")
            while self.running:
                try:
                    conn, _ = server_sock.accept()
                    threading.Thread(target=self.handle_client_connection, args=(conn,), daemon=True).start()
                except Exception as e:
                    print(f"[Gateway] Erro ao aceitar conexão: {e}")

    def handle_client_connection(self, conn):
        try:
            while True:
                data = conn.recv(1024)
                if not data:
                    print("[Gateway] Cliente desconectado.")
                    break

                request = gateway_pb2.ClientRequest()
                request.ParseFromString(data)

                if request.request_type == "list_devices":
                    self.send_device_list(conn)
                elif request.request_type == "send_command":
                    self.forward_command_to_device(request.device_id, request.command, request.value, conn)
        except Exception as e:
            print(f"[Gateway] Erro na conexão com o cliente: {e}")
        finally:
            conn.close()
            print("[Gateway] Conexão encerrada com o cliente.")

    def check_device_status(self):
        inactive_devices = []
        for device_id, (ip, port, device_type, state) in list(self.devices.items()):
            try:
                with socket.create_connection((ip, port), timeout=2) as sock:
                    pass  # Conexão bem-sucedida, o dispositivo está ativo
            except Exception:
                inactive_devices.append(device_id)

        for device_id in inactive_devices:
            print(f"[Gateway] Dispositivo {device_id} está inativo e será removido.")
            del self.devices[device_id]

    def send_device_list(self, conn):
        self.check_device_status()

        response = gateway_pb2.ClientResponse()
        response.status = "success"
        for device_id, (ip, port, device_type, state) in self.devices.items():
            device_info = response.devices.add()
            device_info.device_id = device_id
            device_info.device_type = device_type
            device_info.state = state

        conn.sendall(response.SerializeToString())

    def forward_command_to_device(self, device_id, command, value, conn):
        if device_id not in self.devices:
            response = gateway_pb2.ClientResponse()
            response.status = "error"
            response.message = f"Device {device_id} not found."
            conn.sendall(response.SerializeToString())
            return

        ip, port, _, _ = self.devices[device_id]
        print(f"[Gateway] Tentando conectar ao dispositivo {device_id} no endereço {ip}:{port}")

        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as device_sock:
                device_sock.connect((ip, port))
                device_sock.sendall(f"{command},{value}".encode())
                ack = device_sock.recv(1024).decode()

                response = gateway_pb2.ClientResponse()
                response.status = "success"
                response.message = ack
                conn.sendall(response.SerializeToString())
        except Exception as e:
            print(f"[Gateway] Erro ao conectar ao dispositivo {device_id}: {e}")
            response = gateway_pb2.ClientResponse()
            response.status = "error"
            response.message = str(e)
            conn.sendall(response.SerializeToString())

    def shutdown_gateway(self, signum, frame):
        print("[Gateway] Encerrando...")
        self.running = False
        sys.exit(0)

if __name__ == "__main__":
    gateway = Gateway()
    gateway.start_gateway()

    while gateway.running:
        time.sleep(1)
