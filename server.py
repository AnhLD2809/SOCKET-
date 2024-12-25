import socket
import os
import sys
import threading
import stat

PORT = 8081
FILE_PATH = "E:\\2024.1\\MMT\\files_server"
PASSWORD = "nhom1"

def send_file(client_socket, filename):
    filepath = os.path.join(FILE_PATH, filename)

    try:
        with open(filepath, "rb") as file:
            while True:
                bytes_read = file.read(1024)
                if not bytes_read:
                    break
                client_socket.sendall(bytes_read)
    except Exception as e:
        print(f"Error sending file: {e}")

def list_files_recursively(base_path, file_list):
    for entry in os.listdir(base_path):
        full_path = os.path.join(base_path, entry)
        if os.path.isfile(full_path):
            relative_path = os.path.relpath(full_path, FILE_PATH)
            file_list.append(relative_path)
        elif os.path.isdir(full_path):
            list_files_recursively(full_path, file_list)

def list_files(client_socket):
    file_list = []
    list_files_recursively(FILE_PATH, file_list)

    # Simplified serialization (use a better method like JSON in real code)
    response = f"{len(file_list)}\0" + "\0".join(file_list) + "\0"
    try:
        client_socket.sendall(response.encode())
    except Exception as e:
        print(f"Error sending file list: {e}")

def find_new_filename(filename):
    new_filename = filename
    name, ext = os.path.splitext(filename)
    t = 0
    while True:
        a = 0
        for f in os.listdir(FILE_PATH):
            if f == new_filename:
                a = 1
                t += 1
                new_filename = f"{name}_{t}{ext}"
                break
        if a == 0:
            break
    return new_filename

def receive_file(client_socket, filename):
    filepath = os.path.join(FILE_PATH, filename)

    try:
        with open(filepath, "wb") as file:
            while True:
                bytes_read = client_socket.recv(1024)
                if not bytes_read:
                    break
                file.write(bytes_read)
        print(f"File '{filename}' received successfully.")
    except Exception as e:
        print(f"Error receiving file: {e}")

def upload_confirm(client_socket):
    request = "agree_to_upload"
    client_socket.sendall(request.encode())

def upload_refuse(client_socket):
    request = "refuse_to_upload"
    client_socket.sendall(request.encode())

def lets_upload(client_socket):
    request = "let's_upload"
    client_socket.sendall(request.encode())

def client_handler(client_socket, client_address):
    try:
        while True:
            buffer = client_socket.recv(1024).decode()
            if not buffer:
                break

            print(f"Received from {client_address}: {buffer}")
            if buffer == "list":
                list_files(client_socket)
            elif buffer.startswith("send"):
                filename = buffer[4:]
                file = open(filename, "wb")
                client_socket = file.read(1024)
                send_file(client_socket, filename)
            elif buffer.startswith("upload"):
                password = buffer[6:]
                if password == PASSWORD:
                    upload_confirm(client_socket)
                    # Wait for the next message with filename, ideally this would be part of a protocol
                    filename = client_socket.recv(1024).decode()[len(PASSWORD):] # This is still vulnerable
                    if filename:
                        lets_upload(client_socket)
                        new_filename = find_new_filename(filename)
                        receive_file(client_socket, new_filename)
                else:
                    upload_refuse(client_socket)
            elif buffer.startswith(PASSWORD):
                filename = buffer[len(PASSWORD):]
                new_filename = find_new_filename(filename)
                lets_upload(client_socket)
                receive_file(client_socket, new_filename)
            else:
                print("Invalid request.")
    except Exception as e:
        print(f"Error handling client {client_address}: {e}")
    finally:
        client_socket.close()
        print(f"Connection with {client_address} closed.")

def main():
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1) # Allow address reuse

    server_addr = ("0.0.0.0", PORT)  # Bind to all available interfaces

    try:
        server_socket.bind(server_addr)
        server_socket.listen(5)
        print(f"Server listening on port {PORT}")

        while True:
            client_socket, client_address = server_socket.accept()
            print(f"Accepted connection from {client_address}")
            client_thread = threading.Thread(target=client_handler, args=(client_socket, client_address))
            client_thread.start()
    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        server_socket.close()

if __name__ == "__main__":
    main()