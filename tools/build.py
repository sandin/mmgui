# encoding: utf-8
import os
import sys
import subprocess
import shutil
import traceback
import urllib.request

_my_full_path_ = os.path.abspath(__file__)
_my_dir_ = os.path.dirname(_my_full_path_)

tasks = {}
def task(name, depends):
    def inner_task(func):
        #print("register_task, name=%s" % (name))
        tasks[name] = [func, depends]
        def wrap(*largs, **kwargs):
            return func(*largs, **kwargs)
        return wrap
    return inner_task


@task(name = "clean", depends = [])
def task_clean():
    shutil.rmtree("./build", ignore_errors=True)
    shutil.rmtree("./dist", ignore_errors=True)
    os.mkdir("build")
    os.mkdir("dist")
    return True


@task(name = "ui", depends = [])
def task_ui():
    _my_full_path_ = os.path.abspath(__file__)
    _my_dir_ = os.path.dirname(_my_full_path_)
    src_dir = os.path.join(_my_dir_, "..", 'mmgui')

    def run(cmd):
        print("[exec] %s" % ' '.join(cmd))
        subprocess.check_call(cmd)

    run(['pyrcc5', os.path.join(src_dir, 'res.qrc'), '-o', os.path.join(src_dir, 'res_rc.py')])

    for root, dirs, files in os.walk(src_dir):
        for file in files:
            path = os.path.join(root, file)
            if path.endswith('.ui'):
                dst = os.path.join(root, file[:-3] + '.py')
                run(['pyuic5', path, '--import-from=mmgui', '-o', dst])
    return True


@task(name = "wheel", depends = ["ui"])
def task_wheel():
    subprocess.check_call(['python', 'setup.py', 'sdist']) # twine upload dist/*
    return True


@task(name = "nsis", depends = ["wheel"])
def task_nsis():
    subprocess.check_call(['python', 'build_nsis.py'])
    return True


@task(name = "help", depends = [])
def task_help():
    global tasks
    print("Usage: build [task_name]")
    for task_name in tasks:
        print("\tTask: %s" % task_name)
    return True


@task(name = "download_extensions", depends = [])
def task_download_extensions():
    urls = {
    }
    for dirname, url in urls.items():
        if url.startswith("http"):
            # download zip file
            tmp_file = os.path.join(_my_dir_, "extensions", os.path.basename(url))
            if os.path.exists(tmp_file):
                os.remove(tmp_file)
            urllib.request.urlretrieve(url, os.path.join("extensions", tmp_file))
            print("download file %s -> %s" % (url, tmp_file))
        else:
            tmp_file = url

        # unzip
        output_dir = os.path.join(_my_dir_, "extensions", dirname)
        if os.path.exists(output_dir):
            shutil.rmtree(output_dir, ignore_errors=True)
        shutil.unpack_archive(tmp_file, output_dir)
        os.remove(tmp_file)
        print("unzip file %s -> %s" % (tmp_file, output_dir))
    return True

@task(name = "all", depends = ["clean", "download_extensions", "nsis"])
def task_all():
    return True


def execute_task(task_name):
    global tasks
    task_func, depends = tasks[task_name] if task_name in tasks else None
    if not task_func:
        print("Error: `%s` task is not exists!" % task_name)
    if depends:
        for depend_task_name in depends:
            if not execute_task(depend_task_name):
                return False
    result = False
    print("------------------------------------")
    print("Execute Task: %s\n" % task_name)
    try:
        result = task_func()
    except:
        traceback.print_exc()
    print("\nExecute Task: %s, Result: %s" % (task_name, ("Success" if result else "Fail")))
    print("------------------------------------")
    return result


def main():
    task_name = "all" # default task
    if len(sys.argv) > 1:
        task_name = sys.argv[1]

    print("--- TPT Build System ----")
    print("Target Task: `%s`" % task_name)
    result = execute_task(task_name)
    print("Build Result: %s" % ("Success" if result else "Fail"))

if __name__ == "__main__":
    main()