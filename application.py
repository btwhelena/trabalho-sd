import socket
import sys
import smart_environment_pb2 as gateway_pb2

GATEWAY_ADDRESS = ('localhost', 6000)

class Application:
    def __init__(self):
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.connect_to_gateway()

    def connect_to_gateway(self):
        try:
            self.socket.connect(GATEWAY_ADDRESS)
            print("[Application] Conectado ao Gateway.")
        except Exception as e:
            print(f"[Application] Erro ao conectar ao Gateway: {e}")
            sys.exit(1)

    def send_request(self, request):
        try:
            self.socket.sendall(request.SerializeToString())
            response_data = self.socket.recv(4096)
            response = gateway_pb2.ClientResponse()
            response.ParseFromString(response_data)
            return response
        except Exception as e:
            print(f"[Application] Erro ao enviar requisição: {e}")
            return None

    def list_devices(self):
        request = gateway_pb2.ClientRequest()
        request.request_type = "list_devices"
        response = self.send_request(request)

        if response and response.status == "success":
            print("\nDispositivos conectados:")
            for device in response.devices:
                print(f"- ID: {device.device_id}, Tipo: {device.device_type}, Estado: {device.state}")
        else:
            print("[Application] Não foi possível obter a lista de dispositivos.")

    def send_command(self):
        device_id = input("Digite o ID do dispositivo: ")
        command = input("Digite o comando (toggle/set_temperature): ")
        value = ""

        if command == "set_temperature":
            value = input("Digite a nova temperatura: ")

        request = gateway_pb2.ClientRequest()
        request.request_type = "send_command"
        request.device_id = device_id
        request.command = command
        request.value = value

        response = self.send_request(request)

        if response and response.status == "success":
            print(f"[Application] Comando enviado com sucesso: {response.message}")
        else:
            print(f"[Application] Erro ao enviar comando: {response.message if response else 'Erro desconhecido.'}")

    def run(self):
        while True:
            print("\n[Application] Menu de opções:")
            print("1. Listar dispositivos conectados")
            print("2. Enviar comando para dispositivo")
            print("3. Sair")

            option = input("Escolha uma opção: ")

            if option == "1":
                self.list_devices()
            elif option == "2":
                self.send_command()
            elif option == "3":
                print("[Application] Encerrando aplicação.")
                self.socket.close()
                break
            else:
                print("[Application] Opção inválida. Tente novamente.")

if __name__ == "__main__":
    app = Application()
    app.run()