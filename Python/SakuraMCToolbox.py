import os, re, chardet

def get_encoding(file: str) -> str:
    with open(file, "rb") as f:
        return chardet.detect(f.read())["encoding"]

#check if javaw.exe is running
def check_mc() -> bool:
    return "javaw.exe" in os.popen("tasklist").read()

#stop javaw.exe from running
def stop_mc() -> bool:
    return "成功" in os.popen("taskkill -f -im javaw.exe").read()

def get_token() -> dict:
    if not check_mc(): return None
    result = os.popen("wmic process where caption=\"javaw.exe\" get caption,commandline").read()
    return {
        "authlib": [it for it in result.split(";") if "authlib" in it][0],
        "username": re.findall(r"--username (.+?) ", result)[0],
        "uuid": re.findall(r"--uuid (.+?) ", result)[0],
        "accessToken": re.findall(r"--accessToken (.+?) ", result)[0]
    }

#paramter file, token
def replace_token(file: str, token: dict) -> str: 
    with open(file, "r", encoding = get_encoding(file)) as f:
        text = "\n".join(f.readlines())

    with open(file, "w+", encoding = get_encoding(file)) as launch:
        text = re.sub(r"--username .+? ", "--username " + token["username"] + " ", text)
        text = re.sub(r"--uuid .+? ", "--uuid " + token["uuid"] + " ", text)
        text = re.sub(r"--accessToken .+? ", "--accessToken " + token["accessToken"] + " ", text)
        #delete useless lines
        while "\n\n" in text: text = text.replace("\n\n", "\n")
        launch.write(text)

    return text

#paramter file, token
#file: launch bat, to get the current authlib path
def replace_authlib(file: str, token: dict) -> str:
    server_authlib: str = token["authlib"]
    name = server_authlib.split("/")[-1]
    version = re.findall(r"authlib-(.+?).jar", name)[0]
    with open(file, "r", encoding = get_encoding(file)) as f:
        text = "\n".join(f.readlines())
    game_dir = re.findall(r";(.+?libraries)", text)[0]
    new_authlib_dir = game_dir + "\\com/mojang/authlib/" + version
    new_authlib = new_authlib_dir + "/" + name

    #copy jar
    if not os.path.exists(new_authlib_dir): os.mkdir(new_authlib_dir)
    os.system(("copy \"" + server_authlib + "\" \"" + new_authlib + "\"").replace("\\\\", "\\").replace("/", "\\"))

    #change launch bat's authlib dir
    text = text.replace([it for it in text.split(";") if "authlib" in it][0], new_authlib)
    while "\n\n" in text: text = text.replace("\n\n", "\n")
    with open(file, "w+", encoding = get_encoding(file)) as launch:
        launch.write(text)
    
    return text

#ui
import tkinter as tk
from tkinter import scrolledtext
from tkinter import filedialog
from tkinter import messagebox as msgbox
import traceback
from threading import Thread

#main windows
ui = tk.Tk()
ui.title("Sakura Minecraft Toolbox v1.3 released | Python3 ver.")
ui.resizable(False, False)

input = tk.LabelFrame(ui, text = "Input", fg = "#FF69B4", font = ("Consolas", 10), padx = 10, pady = 10)
input.grid(padx = 20, pady = 20, row = 0, column = 0, sticky = tk.N)

output = tk.LabelFrame(ui, text = "Output", fg = "#FF69B4", font = ("Consolas", 10), padx = 10, pady = 10)
output.grid(padx = 20, pady = 20, row = 0, column = 1, sticky = tk.N)

output_window = scrolledtext.ScrolledText(output, width = 30, height = 12, padx = 10, pady = 10, wrap = tk.W, font = ("微软雅黑", 10), state = "disabled")
output_window.grid()

def log(string: str):
    output_window.config(state = "normal")
    output_window.insert("end", string + "\n")
    output_window.see("end")
    output_window.config(state = "disabled")

bat_path_value = tk.StringVar()#路径选择
bat_path = tk.Entry(input, textvariable = bat_path_value, font = ("微软雅黑", 10), width = 20)
bat_path.grid(padx = 5, pady = 5, row = 0, columnspan = 2)

bat_path_select = tk.Button(input, text = "启动脚本选择", font = ("微软雅黑", 11), command = lambda: bat_path_value.set(filedialog.askopenfilename(filetypes = [("Minecraft启动脚本", "*.bat *.cmd")])))
bat_path_select.grid(padx = 5, pady = 5, row = 0, column = 2)

token_cache = None

def get_uuid_command():
    global token_cache
    token_cache = get_token()
    log("获取成功: \n " + str(token_cache).replace("{", "").replace("}", "") if token_cache else "获取失败! 请启动游戏后使用.")

get_uuid = tk.Button(input, text = "获取参数", font = ("微软雅黑", 11), command = get_uuid_command)
get_uuid.grid(pady = 4, row = 1, column = 0)

def run_game_command():
    if not bat_path_value.get():
        log("请指定启动脚本路径!")
        return
    log("游戏已经启动.")
    os.system("\"" + bat_path_value.get() + "\"")

run_game = tk.Button(input, text = "启动游戏", font = ("微软雅黑", 11), command = lambda: Thread(target = run_game_command).start())
run_game.grid(pady = 4, row = 2, column = 0)

close_game = tk.Button(input, text = "关闭游戏", font = ("微软雅黑", 11), command = lambda: log("关闭成功." if stop_mc() else "关闭失败!"))
close_game.grid(pady = 4, row = 2, column = 1)

close_box = tk.Button(input, text = "关闭快吧", font = ("微软雅黑", 11), command = lambda: log("关闭成功." if "成功" in os.popen("taskkill -f -im k8mc.exe").read() else  "关闭失败!"))
close_box.grid(pady = 4, row = 2, column = 2)

def replace_uuid_command():
    if (not bat_path_value.get()):
        log("请指定启动脚本路径!")
        return

    if (not token_cache):
        log("请先获取启动参数!")
        return

    try:
        replace_token(bat_path_value.get(), token_cache)
    except:
        msgbox.showerror(title = "ERROR", message = traceback.format_exc())
        log("参数替换失败! 请确认使用正确, 或向他人寻求帮助.")
    else:
        log("参数替换完毕. 若未替换过authlib请点击替换, 否则可以点按启动.")

replace_uuid = tk.Button(input, text = "替换参数", font = ("微软雅黑", 11), command = replace_uuid_command)
replace_uuid.grid(pady = 4, row = 1, column = 1)

def replace_authl1b_command():
    if (not bat_path_value.get()):
        log("请指定启动脚本路径!")
        return

    if (not token_cache):
        log("请先获取启动参数!")
        return

    try:
        replace_authlib(bat_path_value.get(), token_cache)
    except:
        msgbox.showerror(title = "ERROR", message = traceback.format_exc())
        log("authlib替换失败! 请确认使用正确, 或向他人寻求帮助.")
    else:
        log("authlib替换完毕.")

replace_authl1b = tk.Button(input, text = "替换authlib", font = ("微软雅黑", 11), command = replace_authl1b_command)
replace_authl1b.grid(pady = 4, row = 1, column = 2)

description_text = tk.Label(input, fg = "#FF69B4", font = ("微软雅黑", 9), text = "1. 准备好欲使用的启动脚本\n2. 启动欲代替的游戏(如快吧盒子)\n3. 获取启动参数(username, uuid, accessToken)\n 4. 关闭已经打开的游戏\n 5. 替换启动参数(及authlib)\n6. 点击\"启动游戏\", 将会使用替换后的脚本启动")
description_text.grid(pady = 4, row = 3, columnspan = 3)

bottom_text = tk.Label(ui, fg = "#FF69B4", font = ("Consolas", 10), text = "Copyright 2021 Kirisame")
bottom_text.grid(sticky = tk.S, columnspan = 2)

import json

def close_window():
    if msgbox.askokcancel("退出", "确定要退出工具箱吗?"):
        with open("sakura.json", "w+", encoding = "utf-8") as config:
            config.write(json.dumps({
                "bat": bat_path_value.get(),
                "token": token_cache
            }))
        ui.destroy()

ui.protocol("WM_DELETE_WINDOW", close_window)

if not os.path.isfile("sakura.json"):
    msgbox.showinfo("Welcome", "欢迎使用Sakura开端助手, 一款免费且开源的工具!\n版本1.3更新日志:\n1. 使用新的模块用来自动识别启动脚本的编码.\n2. 添加缓存机制, 不必每次打开都选择脚本路径.")
else:
    with open("sakura.json", "r", encoding = "utf-8") as config:
        try:
            config_dict: dict = json.loads("".join(config.readlines()))
            bat_path_value.set(config_dict["bat"])
            token_cache = config_dict["token"]
            if token_cache:
                log("已经载入之前的参数:\n" + str(token_cache).replace("{", "").replace("}", ""))
        except:
            pass

ui.mainloop()         
