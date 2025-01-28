import sys
import asyncio
from constants import *
import json
import os
"""
{
type: LOGIN
username:
password:
}
"""
user_list = []

def clear_screen():
    # For Windows
    if os.name == 'nt':
        os.system('cls')
    # For Linux/macOS
    else:
        os.system('clear')

async def write_messages(writer):

    msg = {}
    while True:
        message = await asyncio.to_thread(sys.stdin.readline)
        # encode the string message to bytes
        msg_bytes = message.encode()
        # transmit the message to the server
        writer.write(msg_bytes)
        # wait for the buffer to be empty
        await writer.drain()
        if message.strip() == 'QUIT':
            break
    print('Quitting...')

async def display_clients(users):
    clear_screen()
    for i, user in enumerate(users):
        print(f"{i+1}. {user}")

async def choose_user(writer):
    choice = await asyncio.to_thread(sys.stdin.readline)
    while choice not in range(1, len(user_list)+1):
        choice = await asyncio.to_thread(sys.stdin.readline)
    
    data = {}
    data['type'] = CHAT_REQUEST
    data['destination'] = user_list[choice]
    msg = json.dumps(data)
    msg += '\n'
    writer.write(msg.encode())
    await writer.drain()
    return user_list[choice]



CHAT_SESSION = False
async def start_chat_session():
    CHAT_SESSION = True
    clear_screen()



async def read_messages(reader, writer):
    while True:
        msg = {}
        result_bytes = await reader.readline()
        response = result_bytes.decode()
        msg = json.loads(response)

        if msg['type'] == USERS and not CHAT_SESSION:
            users = msg['users']
            global user_list
            user_list = users
            display_clients(users)
        if msg['type'] == CHAT_OK:
            start_chat_session()
        
        if msg['type'] == CHAT and CHAT_SESSION:
            print(msg['message'])
        if msg['type'] == CHAT_REQUEST:
            if CHAT_SESSION:
                data = {'type': REQ_DEN}
                msg = json.dumps(data)
                msg += '\n'
                writer.write(msg.encode())
                await writer.drain()

            print("Do you want to chat? Y/N")
            choice = await asyncio.to_thread(sys.stdin.readline)
            if choice == 'Y':
                data = {'type': REQ_ACC}
                msg = json.dumps(data)
                msg += '\n'
                writer.write(msg.encode())
                await writer.drain()
                
            else:
                data = {'type': REQ_DEN}                
                msg = json.dumps(data)
                msg += '\n'
                writer.write(msg.encode())
                await writer.drain()

        print(response.strip())
 
def display_menu():
    print("Welcome to my Chat Server")
    print("1. New User?")
    print("2. Existing User?")
    print("3. Quit")
    try:
        choice = int(input("Enter your choice: "))
        return choice
    except ValueError:
        print("Invalid choice. Please enter a number.")
        return 0

async def sign_up(reader, writer):
    data = {}
    data['type'] = SIGNUP
    data['username'] = input('Enter username: ')
    data['password'] = input('Enter password: ')
    msg = json.dumps(data)
    print(msg)
    msg += '\n'
    writer.write(msg.encode())
    await writer.drain()


    response = await reader.readline()
    response = json.loads(response.decode())
    print(response)
    if response['status'] == OK:
        print('Signup successful.')
        return True
    else:
        print(response['message'])
        return False


async def login(reader, writer):
    data = {}
    data['type'] = LOGIN
    data['username'] = input('Enter username: ')
    data['password'] = input('Enter password: ')
    msg = json.dumps(data)
    msg += '\n'
    writer.write(msg.encode())
    await writer.drain()

    response = await reader.readline()
    response = json.loads(response.decode())
    print(response)
    if response['status'] == OK:
        print('Login successful.')
        return True
    else:
        print(response['message'])
        return False

async def main():
    server_address, server_port = '127.0.0.1', 8888
    print(f'Connecting to {server_address}:{server_port}...')
    reader, writer = await asyncio.open_connection(server_address, server_port)
    print('Connected.')
    ch = display_menu()
    while True:
        if ch == 1:
            if await sign_up(reader, writer):
                break

        elif ch == 2:
            if await login(reader, writer):
                break
        elif ch == 3:
            exit(0)
        else:
            ch = display_menu()
        print("Hi")

    print("Authentication part successfull")

    read_task = asyncio.create_task(read_messages(reader, writer))


    while True:
        if not CHAT_SESSION:
            await choose_user(writer)
        else:
            await write_messages(writer)
    read_task.cancel()
    print('Disconnecting from server...')
    writer.close()
    await writer.wait_closed()
    print('Done.')
 

asyncio.run(main())