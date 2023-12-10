import json
import os
import datetime


class FileOperation:
    def ReadJSon(file_path):
        with open(file_path, "r", encoding="utf-8") as file:
            data = json.load(file)
        return data

    def WriteJson(file_path, data):
        with open(file_path, "w", encoding="utf-8") as file:
            json.dump(data, file, indent=4, ensure_ascii=False)

    def CreateJson(file_path, data):
        if not os.path.exists(os.path.dirname(file_path)):
            try:
                os.makedirs(os.path.dirname(file_path))
            except OSError as e:
                if e.errno != os.errno.EEXIST:
                    raise
        if not os.path.exists(file_path):
            with open(file_path, "w") as file:
                json.dump(data, file)

    def CreateText(file_path, data):
        if not os.path.exists(os.path.dirname(file_path)):
            try:
                os.makedirs(os.path.dirname(file_path))
            except OSError as e:
                if e.errno != os.errno.EEXIST:
                    raise
        if not os.path.exists(file_path):
            with open(file_path, "w") as file:
                file.write(data)

    def WriteText(file_path, data):
        with open(file_path, "w") as file:
            file.write(data)

    def ReadText(file_path):
        with open(file_path, "r") as file:
            return file.context()


class Logger:
    def Info(data):
        print(
            f"\033[32m{Logger.GetTime()} \033[0m|\033[32m INFO \033[0m| {data}\033[0m "
        )

    def Warning(data):
        print(
            f"\033[32m{Logger.GetTime()} \033[0m|\033[32m WARN \033[0m|\033[32m {data}\033[0m "
        )

    def Error(data):
        print(
            f"\033[32m{Logger.GetTime()} \033[0m|\033[31m ERROR \033[0m |\033[31m {data}\033[0m "
        )

    def Debug(data, Debug_mode):
        """发送一个调试 `Log`
        #### 参数：
            - data `string` 内容
        """
        if Debug_mode:
            print(
                f"\033[32m{Logger.GetTime()} \033[0m|\033[34m DEBUG \033[0m|\033[34m {data}\033[0m "
            )

    def GetTime():
        """获取当前时间"""
        current_time = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        return current_time
