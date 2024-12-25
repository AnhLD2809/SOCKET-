import socket
import os
import sys

PORT = 8081
SERVER_IP = "127.0.0.1"
FILE_PATH = ".\\files_client"

def error(message):
    print(message)
    sys.exit(1)

def receive_file(socket_fd, filename):
    filepath = os.path.join(FILE_PATH, filename)

    try:
        with open(filepath, "wb") as file:
            while True:
                bytes_read = socket_fd.recv(1024)
                if not bytes_read:
                    break
                file.write(bytes_read)
                break
        print(f"{filename} has been received.")
    except Exception as e:
        error(f"Error receiving file: {e}")

def upload_file(socket_fd, filename):
    filepath = os.path.join(FILE_PATH, filename)

    try:
        with open(filepath, "rb") as file:
            while True:
                bytes_read = file.read(1024)
                if not bytes_read:
                    break
                socket_fd.sendall(bytes_read)
    except Exception as e:
        error(f"Error uploading file: {e}")

def list_files(socket_fd):
    request = "list"
    socket_fd.sendall(request.encode())

    receive_list = socket_fd.recv(4096)  # Adjust buffer size as needed
    
    # Deserialize the received data (simplified for demonstration)
    # In a real scenario, you'd need a more robust way to parse the data
    
    file_list = []
    try:
      decoded_data = receive_list.decode('utf-8', errors='ignore') # Decode with error handling
      if decoded_data:
          parts = decoded_data.split('\0') # Assuming filenames are null-terminated
          num_files = int(parts[0])
          file_list = parts[1:num_files+1]
      else:
        print("Received empty list from server.")

    except UnicodeDecodeError:
      print("Error: Received data could not be decoded as UTF-8. Check server-side encoding.")
      return []
    except ValueError:
        print("Error: Could not extract the number of files from the response")
        return []
    except IndexError:
        print("Error: Received data does not match expected format")
        return []

    print("======= List files on server ======")
    for filename in file_list:
        print(filename)

    return file_list

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

def upload_confirm(socket_fd):
    buffer = socket_fd.recv(1024).decode()
    if buffer == "agree_to_upload":
        return 1
    elif buffer == "refuse_to_upload":
        return 0
    else:
        socket_fd.close()
        return 0

def lets_upload(socket_fd):
    buffer = socket_fd.recv(1024).decode()
    if buffer == "let's_upload":
        return 1
    else:
        return 0

def list_files_recursively(base_path, file_list):
    for entry in os.listdir(base_path):
        full_path = os.path.join(base_path, entry)
        if os.path.isfile(full_path):
            relative_path = os.path.relpath(full_path, FILE_PATH)
            file_list.append(relative_path)
            print(relative_path)
        elif os.path.isdir(full_path):
            list_files_recursively(full_path, file_list)
            
def list_files_upload():
    file_list = []
    print("======== List files upload ======== ")
    list_files_recursively(FILE_PATH, file_list)
    return file_list

def clear_input_buffer():
    pass  # Not needed in Python

def main():
    
    while True:
        try:
            socket_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_addr = (SERVER_IP, PORT)
            socket_fd.connect(server_addr)
        except ConnectionRefusedError:
            print("Connection to server failed. Is the server running?")
            return
        except Exception as e:
            print(f"An unexpected error occured: {e}")
            return

        print("====== Please choose a service ======")
        print("1. List file")
        print("2. Download")
        print("3. Upload")
        print("4. Exit")

        try:
            choice = int(input("Enter your choice: "))
        except ValueError:
            print("Invalid input. Please enter a number.")
            socket_fd.close()
            continue

        if choice == 1:
            list_files(socket_fd)
        elif choice == 2:
            server_file_list = list_files(socket_fd)
            socket_fd.close()  # Close the socket after getting the list
            while True:
                filepath = input("Enter the file name (file path) to download or 'quit' to exit: ")
                if filepath == "quit":
                    break

                if filepath in server_file_list:
                    filename = os.path.basename(filepath)
                    new_filename = find_new_filename(filename)

                    try:
                        socket_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        socket_fd.connect((SERVER_IP, PORT))  # Reconnect for each download
                        request = f"download {filepath}"
                        socket_fd.sendall(request.encode())
                        receive_file(socket_fd, new_filename)
                    except Exception as e:
                        print(f"Error during download: {e}")
                    finally:
                        socket_fd.close()  # Close the socket after each download
                else:
                    print("File does not exist. Please try again.")
                
        elif choice == 3:
            b = 1
            while b:
                try:
                  socket_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                  socket_fd.connect(server_addr)
                except ConnectionRefusedError:
                    print("Connection to server failed. Is the server running?")
                    break
                except Exception as e:
                    print(f"An unexpected error occured: {e}")
                    break
                password = input("Enter the password or 'quit' to exit: ")

                if password == "quit":
                    socket_fd.close()
                    break

                request = f"upload{password}"
                socket_fd.sendall(request.encode())
                if upload_confirm(socket_fd):
                    b = 0
                    local_file_list = list_files_upload()
                    while True:
                        filepath = input("Enter the file name (file path) to upload or 'quit' to exit: ")

                        if filepath == "quit":
                            break

                        if filepath in local_file_list:
                            filename = os.path.basename(filepath)
                            try:
                              socket_fd = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                              socket_fd.connect(server_addr)
                              request = f"{password}{filename}"
                              socket_fd.sendall(request.encode())

                              if lets_upload(socket_fd):
                                  upload_file(socket_fd, filepath)
                                  print(f"Upload {filename} successfully.")

                            except Exception as e:
                                print(f"Error during upload: {e}")
                            finally:
                                socket_fd.close()

                        else:
                            print("File does not exist. Please try again.")
                else:
                    print("Incorrect password, please enter again.")
                
        elif choice == 4:
            socket_fd.close()
            sys.exit(0)
        else:
            print("Invalid choice. Please try again.")

        socket_fd.close()

if __name__ == "__main__":
    main()