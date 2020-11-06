import os
import subprocess
import sys
import logging
from subprocess import list2cmdline
logger = logging.getLogger(__file__)

ORIGINAL_STDIO = {

}
STDOUT_STREAMS = set()
STDERR_STREAMS = set()

if sys.platform == 'win32':
    from _ctypes import Structure, POINTER
    from ctypes import *
    from ctypes.wintypes import *

    class PROCESSENTRY32(Structure):
        _fields_ = [
            ('dwSize', DWORD),
            ('cntUsage', DWORD),
            ('th32ProcessID', DWORD),
            ('th32DefaultHeapID', POINTER(ULONG)),
            ('th32ModuleID', DWORD),
            ('cntThreads', DWORD),
            ('th32ParentProcessID', DWORD),
            ('pcPriClassBase', LONG),
            ('dwFlags', DWORD),
            ('szExeFile', c_char * MAX_PATH)
        ]

    psapi = windll.psapi

    CreateToolhelp32Snapshot= windll.kernel32.CreateToolhelp32Snapshot
    Process32First = windll.kernel32.Process32First
    Process32Next = windll.kernel32.Process32Next
    GetLastError = windll.kernel32.GetLastError
    CloseHandle = windll.kernel32.CloseHandle
    TH32CS_SNAPPROCESS = 0x2

    class Process:

        def __init__(self, pid):
            self.pid = pid
            self.ppid = 0
            self.name = None
            self.children = {}

        def set_name(self, name):
            self.name = name

        def set_parent(self, ppid):
            self.ppid = ppid

        def add_child(self, process):
            if process.pid != self.pid:
                self.children[process.pid] = process

        def print(self, layer = 0):
            print("%s+ %d %s" % (' ' * layer, self.pid, self.name if self.name else ""))
            for c in self.children.values():
                c.print(layer + 1)

        def kill(self):
            for c in self.children.values():
                c.kill()
            os.kill(self.pid, 0)

    def get_self_process_tree():

        flat_map = {}

        holder = PROCESSENTRY32()
        holder.dwSize = sizeof(holder)

        hProcessSnap = CreateToolhelp32Snapshot(TH32CS_SNAPPROCESS, os.getpid())
        #print("hProcessEnum", hProcessSnap)

        ret = Process32First(hProcessSnap, pointer(holder))
        while ret:
            pid, ppid = holder.th32ProcessID, holder.th32ParentProcessID
            #print("pid=%d, ppid=%d %s" % (pid, ppid, holder.szExeFile))

            if pid not in flat_map: flat_map[pid] = Process(pid)
            if ppid not in flat_map: flat_map[ppid] = Process(ppid)
            flat_map[pid].set_parent(ppid)
            # flat_map[pid].set_name(holder.szExeFile.decode('gbk'))
            flat_map[ppid].add_child(flat_map[pid])

            ret = Process32Next(hProcessSnap, pointer(holder))

        CloseHandle(hProcessSnap)

        if 0 not in flat_map: flat_map[0] = Process(0)
        for pid in flat_map:
            if flat_map[pid].ppid == 0 and pid not in flat_map[0].children:
                flat_map[0].add_child(flat_map[pid])

        return flat_map[os.getpid()]

    CREATE_BREAKAWAY_FROM_JOB = 0x01000000
    ERROR_ALREADY_EXISTS = 183
    ERROR_ACCESS_DENIED = 5

    class JOBOBJECT_BASIC_LIMIT_INFORMATION(Structure):
        _fields_ = [
            ('PerProcessUserTimeLimit', c_uint64),
            ('PerJobUserTimeLimit', c_uint64),
            ('LimitFlags', c_uint32),
            ('MinimumWorkingSetSize', c_uint64),
            ('MaximumWorkingSetSize', c_uint64),
            ('ActiveProcessLimit', c_uint32),
            ('Affinity', c_uint64),
            ('PriorityClass', c_uint32),
            ('SchedulingClass', c_uint32)
        ]


    class JOBOBJECT_EXTENDED_LIMIT_INFORMATION(Structure):
        _fields_ = [
            ('BasicLimitInformation', JOBOBJECT_BASIC_LIMIT_INFORMATION),
            ('_reserve1', c_char * 0x30),
            ('ProcessMemoryLimit', c_uint64),
            ('JobMemoryLimit', c_uint64),
            ('PeakProcessMemoryUsed', c_uint64),
            ('PeakJobMemoryUsed', c_uint64)
        ]

    class STARTUPINFOW(Structure):
      _fields_ = [
        ("cb", DWORD),
        ("lpReserved",LPWSTR),
        ("lpDesktop", LPWSTR),
        ("lpTitle", LPWSTR),
        ("dwX", DWORD),
        ("dwY", DWORD),
        ("dwXSize", DWORD),
        ("dwYSize", DWORD),
        ("dwXCountChars", DWORD),
        ("dwYCountChars", DWORD),
        ("dwFillAttribute", DWORD),
        ("dwFlags", DWORD),
        ("wShowWindow", WORD),
        ("cbReserved2", WORD),
        ("lpReserved2", LPBYTE),
        ("hStdInput", HANDLE),
        ("hStdOutput", HANDLE),
        ("hStdError", HANDLE)
      ]

    class PROCESS_INFORMATION(Structure):
      _fields_ = [
        ("hProcess", HANDLE),
        ("hThread", HANDLE),
        ("dwProcessId", DWORD),
        ("dwThreadId", DWORD)
      ]

    class SECURITY_ATTRIBUTES(Structure):
      _fields_ = [
        ("nLength", DWORD),
        ("lpSecurityDescriptor", c_void_p),
        ("bInheritHandle", BOOL)
      ]

    JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE = 0x00002000
    JOB_OBJECT_LIMIT_BREAKAWAY_OK = 0x800

    JobObjectBasicLimitInformation = 2
    JobObjectExtendedLimitInformation = 9

    CreateJobObjectW = windll.kernel32.CreateJobObjectW
    CreateJobObjectW.restype = HANDLE
    CreateJobObjectW.argtypes = [c_void_p, c_wchar_p]

    GetCurrentProcess = windll.kernel32.GetCurrentProcess
    GetCurrentProcess.restype = HANDLE

    AssignProcessToJobObject = windll.kernel32.AssignProcessToJobObject
    AssignProcessToJobObject.restype = BOOL
    AssignProcessToJobObject.argtypes = [HANDLE, HANDLE]

    OpenJobObjectW = windll.kernel32.OpenJobObjectW
    TerminateJobObject = windll.kernel32.TerminateJobObject
    TerminateJobObject.restype = BOOL
    TerminateJobObject.argtypes = [HANDLE, c_uint]

    SetInformationJobObject = windll.kernel32.SetInformationJobObject
    SetInformationJobObject.restype = BOOL
    SetInformationJobObject.argtypes = [HANDLE, c_int, POINTER(JOBOBJECT_EXTENDED_LIMIT_INFORMATION), DWORD]

    CreateProcessW = windll.kernel32.CreateProcessW
    CreateProcessW.restype = BOOL
    CreateProcessW.argtypes = [
      c_wchar_p,                        # lpApplicationName
      c_wchar_p,                        # lpCommandLine
      c_void_p,                         # lpProcessAttributes
      c_void_p,                         # lpThreadAttributes
      BOOL,                             # bInheritHandles
      DWORD,                            # dwCreationFlags
      c_void_p,                         # lpEnvironment
      c_wchar_p,                        # lpCurrentDirectory
      POINTER(STARTUPINFOW),            # lpStartupInfo
      POINTER(PROCESS_INFORMATION)      # lpProcessInformation
      ]

    CreateMutexW = windll.kernel32.CreateMutexA
    CreateMutexW.restype = HANDLE
    CreateMutexW.argtypes = [
      POINTER(SECURITY_ATTRIBUTES), # null
      BOOL,
      c_wchar_p
    ]

    OpenMutexW = windll.kernel32.OpenMutexW
    OpenMutexW.restype = HANDLE
    OpenMutexW.argtypes = [
      DWORD,
      BOOL,
      c_wchar_p
    ]

    ReleaseMutex = windll.kernel32.ReleaseMutex
    ReleaseMutex.argtypes = [HANDLE]

    CloseHandle = windll.kernel32.CloseHandle
    CloseHandle.argtypes = [HANDLE]

    WaitForSingleObject = windll.kernel32.WaitForSingleObject
    WaitForSingleObject.restype = DWORD
    WaitForSingleObject.argtypes = [
      HANDLE,
      DWORD
    ]

    ShellExecuteW = windll.shell32.ShellExecuteW
    ShellExecuteW.argtypes = [c_void_p, c_wchar_p,  c_wchar_p, c_wchar_p, c_wchar_p, c_int]

    def run_as_job():
        hProcess = GetCurrentProcess()
        hJob = CreateJobObjectW(None, "Global\\testplus_perftool_job_obj")
        if hJob == 0:
            print("CreateJobObjectW Failed:", GetLastError())
            return
        info = JOBOBJECT_EXTENDED_LIMIT_INFORMATION()
        info.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE | JOB_OBJECT_LIMIT_BREAKAWAY_OK
        # print(sizeof(info))
        if not SetInformationJobObject(hJob, JobObjectExtendedLimitInformation, pointer(info), sizeof(info)):
            print("SetInformationJobObject Failed:", GetLastError())
            return
        if not AssignProcessToJobObject(hJob, hProcess):
            print("AssignProcessToJobObject Failed:", GetLastError())
            return
        # print("ok")
        return hJob

    MUTEX_NAME = "Global\\TestPlusPerformanceToolkit_Is_Running"

    def _self_restart_normal():
        # print([sys.executable] + sys.argv)
        cmd = [sys.executable] + sys.argv
        try:
            logging.info("self_restart: %r", cmd)
            subprocess.Popen(cmd, creationflags=subprocess.CREATE_BREAKAWAY_FROM_JOB)
            logger.info("self_restart ok!")
        except:
            logger.exception("self_restart")
            return False
        return True

    def _self_restart_admin():
        params = subprocess.list2cmdline(sys.argv)
        process = ShellExecuteW(
            None,  # HWND hwnd
            u"runas",  # LPCWSTR lpOperation
            sys.executable,  # LPCWSTR lpFile
            params,  # LPCWSTR lpParameters
            None,  # LPCWSTR lpDirectory,
            1  # INT nShowCmd, SEE_MASK_NO_CONSOLE|SEE_MASK_NOCLOSE_PROCESS )
        )
        return process > 32


    def self_restart(admin=False):
        if admin:
            return _self_restart_admin()
        else:
            return _self_restart_normal()

    def wait_for_previous_process():
        lock = CreateMutexW(None, False, MUTEX_NAME)
        err = GetLastError()
        if err == ERROR_ALREADY_EXISTS:
            WaitForSingleObject(lock, -1)
            return lock
        else:
            WaitForSingleObject(lock, -1)
        return lock


    GetConsoleWindow = windll.kernel32.GetConsoleWindow
    ShowWindow = windll.user32.ShowWindow
    AllocConsole = windll.kernel32.AllocConsole
    AttachConsole = windll.kernel32.AttachConsole
    AttachConsole.argtypes = [
      DWORD
    ]
    GetCurrentProcessId = windll.kernel32.GetCurrentProcessId

    IS_CONSOLE_HIDDEN = False

    def _hide_nothing():
        pass
      
    def _hide_console():
        ShowWindow(GetConsoleWindow(), 0)
        global IS_CONSOLE_HIDDEN
        IS_CONSOLE_HIDDEN = True

    WINDOW_OP_PROXY = {
        "hide": _hide_nothing
    }


    class StreamMux(object):
        # Based on https://gist.github.com/327585 by Anand Kunal
        # Based on http://www.tentech.ca/2011/05/stream-tee-in-python-saving-stdout-to-file-while-keeping-the-console-alive/ by Tennessee
        def __init__(self, arr):
            self.arr = arr
            self.attrs = {}

        def __getattribute__(self, name):
            return object.__getattribute__(self, name)

        def __getattr__(self, name):
            def mk_attr(name):
                def attr_func(*args, **kwargs):
                    ret = None
                    for stream in self.arr:
                        callable = getattr(stream, name)
                        ret = callable(*args, **kwargs)
                    return ret

                return attr_func

            # Could also be a property
            if name not in self.attrs:
                self.attrs[name] = mk_attr(name)
            return self.attrs[name]


    def hide_console():
        WINDOW_OP_PROXY['hide']()
      
    def show_console():
        ShowWindow(GetConsoleWindow(), 5)
        global IS_CONSOLE_HIDDEN
        IS_CONSOLE_HIDDEN = False

    def toggle_console():
        if IS_CONSOLE_HIDDEN:
            show_console()
        else:
            hide_console()


    def setup_console():
        if AllocConsole():
            AttachConsole(GetCurrentProcessId())
            fp = open("CONOUT$", "w")
            STDOUT_STREAMS.add(fp)
            STDERR_STREAMS.add(fp)
            sys.stdin = open("CONIN$", "r")
            WINDOW_OP_PROXY['hide'] = _hide_console
            hide_console()
            return True
        else:
            STDOUT_STREAMS.add(ORIGINAL_STDIO['stdout'])
            STDERR_STREAMS.add(ORIGINAL_STDIO['stderr'])
            return False

    def setup_stdio():
        assert not ORIGINAL_STDIO
        ORIGINAL_STDIO['stdout'], ORIGINAL_STDIO['stderr'] = sys.stdout, sys.stderr
        sys.stdout, sys.stderr = StreamMux(STDOUT_STREAMS), StreamMux(STDERR_STREAMS)
else:
    def setup_stdio():
        pass

    def setup_console():
        pass

    def wait_for_previous_process():
        pass

    def run_as_job():
        pass
    
    def hide_console():
        pass

    
