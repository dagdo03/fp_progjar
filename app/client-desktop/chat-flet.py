import flet as ft
import sys
import time 
import os
import socket
import threading
import json

# Menambahkan jalur ke sys.path
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from chatcli import ChatClient

TARGET_IP = os.getenv("SERVER_IP") or "127.0.0.1"
TARGET_PORT = os.getenv("SERVER_PORT") or "8889"

class Message():
    def __init__(self, username: str, text: str, message_type: str ="chat_message"):
        self.username = username
        self.text = text
        self.message_type = message_type

class ChatMessage(ft.Row):
    def __init__(self, message: Message):
        super().__init__()
        self.vertical_alignment = ft.CrossAxisAlignment.START
        self.controls=[
            ft.CircleAvatar(
                content=ft.Text(self.get_initials(message.username)),
                color=ft.colors.WHITE,
                bgcolor=self.get_avatar_color(message.username),
            ),
            ft.Column(
                [
                    ft.Text(message.username, weight="bold"),
                    ft.Text(message.text, selectable=True),
                ],
                tight=True,
                spacing=5,
            ),
        ]

    def get_initials(self, user_name: str):
        return user_name[:1].capitalize()

    def get_avatar_color(self, user_name: str):
        colors_lookup = [
            ft.colors.AMBER,
            ft.colors.BLUE,
            ft.colors.BROWN,
            ft.colors.CYAN,
            ft.colors.GREEN,
            ft.colors.INDIGO,
            ft.colors.LIME,
            ft.colors.ORANGE,
            ft.colors.PINK,
            ft.colors.PURPLE,
            ft.colors.RED,
            ft.colors.TEAL,
            ft.colors.YELLOW,
        ]
        return colors_lookup[hash(user_name) % len(colors_lookup)]

class ChatApp():
    def __init__(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_address = (TARGET_IP, int(TARGET_PORT))
        try:
            self.sock.connect(self.server_address)
            print(f"Connected to server at {self.server_address}")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
        
        self.cc = ChatClient()
        self.tokenid = self.cc.tokenid
        self.username_dest = None
        self.groupname_dest = None
        self.update = None
        self.chat = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
        )
        
    def main(self, page: ft.Page):
        print("main")
        
        def on_message(message: Message):
            if message.message_type == "chat_message":
                m = ChatMessage(message)
            elif message.message_type == "login_message":
                m = ft.Text(message.text, italic=True, color=ft.colors.BLACK45, size=12)
            self.chat.controls.append(m)
            self.page.update()

        self.page = page
        self.page.title = "Chat Application"

        self.navigation_bar = ft.NavigationBar(
            selected_index=0,
            on_change=self.on_navigation_change,
            destinations=[
                ft.NavigationBarDestination(icon=ft.icons.CHAT, label="Chats"),
                ft.NavigationBarDestination(icon=ft.icons.GROUP, label="Groups"),
            ],
        )
        
        print("tokenid check", self.cc.tokenid)
        if self.cc.tokenid:
            print("tokenid woy", self.cc.tokenid)
            self.page.add(self.navigation_bar)
            self.page.add(self.chats_page())
        else:
            self.page.add(self.login_page())
            self.page.add(self.navigation_bar)

        self.page.pubsub.subscribe(on_message)
        self.page.update()

    def start_receiving_messages(self, inboxType="personal"):
        print("start_receiving_messages")
        def receive_messages():
            print("Thread started")
            while True:
                # if inboxType == "personal":
                response = self.cc.proses("inbox " + self.username_dest)
                print("response inbox", response)
                self.display_message(response)

                time.sleep(1)

        threading.Thread(target=receive_messages, daemon=True).start()

    def display_message(self, message):
        if message['status']:
            if message['status'] == "OK":
                # clear chat
                self.chat.controls.clear()
                for chat_message in message['messages']:
                    self.chat.controls.append(ChatMessage(Message(chat_message['msg_from'], chat_message['msg'])))
                
        self.page.update()

    def register_page(self):
        register = ft.Column()
        username_input = ft.TextField(label="Username")
        register.controls.append(username_input)
        email_input = ft.TextField(label="Email")
        register.controls.append(email_input)
        password_input = ft.TextField(label="Password")
        register.controls.append(password_input)
        register_button = ft.ElevatedButton(text="Register")

        register_rows = ft.Row()
        register_rows.controls.append(register_button)
        login_redirect = ft.TextButton("Already have an account? Login here.")
        register_rows.controls.append(login_redirect)
        register.controls.append(register_rows)

        def on_register_click(e):
            username = username_input.value
            password = password_input.value
            email = email_input.value
            string_send = f"register {username} {email} {password}"
            response = self.cc.proses(string_send)
            self.tokenid = self.cc.tokenid
            if self.tokenid is None:
                print("Register failed")
                return
            print(response)
            self.page.controls.clear()
            self.page.controls.append(self.navigation_bar)
            self.page.update()

        def login_page_redirect(e):
            self.page.controls.clear()
            self.page.controls.append(self.login_page())
            self.page.update()        
          
        register_button.on_click = on_register_click
        login_redirect.on_click = login_page_redirect
        return register
    
    def login_page(self):
        login = ft.Column()
        username_input = ft.TextField(label="Username")
        login.controls.append(username_input)
        password_input = ft.TextField(label="Password")
        login.controls.append(password_input)
        login_rows = ft.Row()

        login_button = ft.ElevatedButton(text="Login")
        register_redirect = ft.TextButton("Don't have an account? Register here.")
        login_rows.controls.append(login_button)
        login_rows.controls.append(register_redirect)

        login.controls.append(login_rows)

        def on_login_click(e):
            username = username_input.value
            password = password_input.value
            string_send = f"auth {username} {password}"
            response = self.cc.proses(string_send)
            self.tokenid = self.cc.tokenid
            if self.tokenid is None:
                print("Login failed")
                return
            print(response)
            self.page.controls.clear()
            self.page.controls.append(self.navigation_bar)
            self.page.update()
          
        def register_page_redirect(e):
            self.page.controls.clear()
            self.page.controls.append(self.register_page())
            self.page.update()

        login_button.on_click = on_login_click
        register_redirect.on_click = register_page_redirect
        return login

    def on_navigation_change(self, e):
        if e.control.selected_index == 0:
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            self.page.add(self.chats_page())
        elif e.control.selected_index == 1:
            self.page.controls.clear()
            self.page.add(self.navigation_bar)
            self.page.add(self.groups_page())
        self.page.update()

    def chats_page(self):
        users = self.cc.proses("users")
        print("USERS", users)

        listuser = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
        )

        for user in list(users.keys()):
            user = users[user]
            chat_message = ChatMessage(Message(user['nama'], user['email']))
            print(user['nama'])
            container = ft.Container(
                content=chat_message,
                on_click=lambda e, username_dest=user['nama']: self.dlg_modal(e, username_dest),
            )
            listuser.controls.append(container)

        return listuser

    def dlg_modal(self, e, username_dest):
        self.username_dest = username_dest


        
        response = self.cc.proses(f"inbox {self.username_dest}")
        print("chats", response)
        
        for chat_message in response['messages']:
            self.chat.controls.append(ChatMessage(Message(chat_message['msg_from'], chat_message['msg'])))

        new_message = ft.TextField()

        def send_click(e):
            if new_message.value == "":
                return
            response = self.cc.proses(f"send {self.username_dest} {new_message.value}")
            print(response)
            self.chat.controls.append(ChatMessage(Message(self.cc.username, new_message.value)))

            new_message.value = ""
            self.page.update()

        self.page.clean()
        self.page.add(
            self.chat, ft.Row(controls=[new_message, ft.ElevatedButton("Send", on_click=send_click)])
        )
        self.page.add(self.navigation_bar)
        self.start_receiving_messages("personal")


    def groups_page(self):
        # Fetch groups from the server using ChatClient
        groups = self.cc.proses("group get")
        print("GROUPS", groups)

        list_groups = ft.ListView(
            expand=True,
            spacing=10,
            auto_scroll=True,
        )

        # Iterate over the groups retrieved and create UI elements to display them
        for group_name in groups:
            group_info = groups[group_name]
            group_container = ft.Container(
                content=ft.Text(group_name),
                on_click=lambda e, groupname=group_name: self.join_group_dialog(e, groupname),
            )
            list_groups.controls.append(group_container)

        return list_groups

    def join_group_dialog(self, e, groupname):
        self.groupname_dest = groupname
        
        response = self.cc.proses(f"group inbox {self.groupname_dest}")
        print("group inbox", response)
        
        # Clear existing chat messages
        self.chat.controls.clear()
        
        for chat_message in response['messages']:
            self.chat.controls.append(ChatMessage(Message(chat_message['msg_from'], chat_message['msg'])))

        new_message = ft.TextField()

        def send_click(e):
            if new_message.value == "":
                return
            response = self.cc.proses(f"group send {self.groupname_dest} {new_message.value}")
            print(response)
            self.chat.controls.append(ChatMessage(Message(self.cc.username, new_message.value)))

            new_message.value = ""
            self.page.update()

        self.page.clean()
        self.page.add(
            self.chat, ft.Row(controls=[new_message, ft.ElevatedButton("Send", on_click=send_click)])
        )
        self.page.add(self.navigation_bar)
        self.start_receiving_messages("group")

ft.app(target=ChatApp().main)
