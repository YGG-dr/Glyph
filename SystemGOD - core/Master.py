# ════════════════════════════════════════════════════════════════════════════════
#                              SystemGOD - MASTER.PY
# ════════════════════════════════════════════════════════════════════════════════
# Command execution system with support for multiple shells (cmd, powershell, bash)
# with robust process management, non-blocking I/O and JSON communication.
# ════════════════════════════════════════════════════════════════════════════════

# O código foi 99% comentado por IA, então não vem me encher o saco depois... >:3

import sys
import json
import subprocess
import os
import threading
import platform
import signal

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                       GLOBAL CONFIGURATION AND STATE                       ║
# ╚════════════════════════════════════════════════════════════════════════════╝

is_windows = platform.system() == "Windows"
valid_shells = {'cmd', 'powershell', 'bash'}

process_lock = threading.Lock()


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                  FUNCTION: ENQUEUE OUTPUT (Stream Reading)                 ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def enqueue_output(stream, stream_type, request_id=None):
    """
    Read streams in separate threads to prevent deadlock.
    
    PARAMETERS:
        stream: input file (stdout/stderr)
        stream_type: stream type for identification ('stdout' or 'stderr')
        request_id: request ID for correlation (optional)
    
    OPERATION:
        - Reads line by line from stream until end
        - Sends each line as JSON to stdout
        - Includes request_id if provided for traceability
        - Handles exceptions and closes stream properly
    """
    try:
        # ┌─ Read loop: iterate while there is data in the pipe
        for line in iter(stream.readline, ''):
            if not line:
                break
            
            # ┌─ Prepare JSON payload with stream type and data
            payload = {
                "type": stream_type, 
                "data": line
            }
            # └─ Add request ID if available
            if request_id:
                payload["id"] = request_id

            # ┌─ Send payload as JSON to stdout
            sys.stdout.write(json.dumps(payload) + "\n")
            sys.stdout.flush()
            # └─
    except (ValueError, OSError):
        # Stream open/closed errors are expected at end of reading
        pass 
    finally:
        # ┌─ Ensure stream is closed
        try:
            stream.close()
        except:
            pass
        # └─



# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                  FUNCTION: KILL CURRENT PROCESS (Termination)              ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def _kill_proc(proc):
    """Kill a single subprocess.Popen instance robustly."""
    try:
        if not proc:
            return
        if proc.poll() is not None:
            return
        if is_windows:
            os.kill(proc.pid, signal.CTRL_BREAK_EVENT)
        else:
            proc.kill()
    except Exception as e:
        sys.stdout.write(json.dumps({"type": "error", "data": f"Error killing process: {str(e)}"}) + "\n")
        sys.stdout.flush()


def kill_current_process(session_id=None):
    """
    Kill process(es) associated with a session.

    If `session_id` is provided, only that session's process is killed.
    If `session_id` is None, all sessions' processes are killed.
    """
    # ┌─ Acquire lock to avoid races when touching session.process
    with process_lock:
        if session_id:
            s = sessions.get(session_id)
            if s and getattr(s, 'process', None):
                _kill_proc(s.process)
                s.process = None
            return

        # kill all sessions
        for s in list(sessions.values()):
            if getattr(s, 'process', None):
                _kill_proc(s.process)
                s.process = None



# ╔════════════════════════════════════════════════════════════════════════════╗
# ║      FUNCTION: EXECUTE COMMAND (Execution with Non-Blocking I/O)           ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def execute_command(session, command):
    """
    Execute a command bound to a TerminalSession.

    The session object's `shell_type`, `cwd` and `id` fields are used.
    The resulting subprocess.Popen is stored in `session.process`.
    """
    shell_type = session.shell_type
    cwd = session.cwd
    request_id = session.id

    # SECTION 1: SHELL PREPARATION AND CONFIGURATION
    shell_args = []
    use_shell_flag = False
    creation_flags = 0
    startupinfo = None

    if is_windows:
        creation_flags = subprocess.CREATE_NEW_PROCESS_GROUP
        startupinfo = subprocess.STARTUPINFO()
        startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

    if shell_type == 'powershell':
        ps_wrapper = f"[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; {command}"
        shell_args = [
            "powershell",
            "-NoProfile",
            "-NoLogo",
            "-NonInteractive",
            "-ExecutionPolicy", "Bypass",
            "-Command", ps_wrapper
        ]
    elif shell_type == 'bash':
        shell_args = ["bash", "-c", command]
    else:
        shell_args = command
        use_shell_flag = True

    # SECTION 2: PROCESS EXECUTION
    try:
        with process_lock:
            proc = subprocess.Popen(
                shell_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE,
                shell=use_shell_flag,
                cwd=cwd,
                text=True,
                bufsize=1,
                encoding='utf-8',
                errors='replace',
                creationflags=creation_flags,
                startupinfo=startupinfo
            )
            session.process = proc

        start_msg = {"type": "start", "pid": proc.pid}
        if request_id:
            start_msg["id"] = request_id
        sys.stdout.write(json.dumps(start_msg) + "\n")
        sys.stdout.flush()

        # SECTION 3: READ THREADS (Non-Blocking I/O)
        t_out = threading.Thread(target=enqueue_output, args=(proc.stdout, 'stdout', request_id))
        t_err = threading.Thread(target=enqueue_output, args=(proc.stderr, 'stderr', request_id))
        t_out.daemon = True
        t_err.daemon = True
        t_out.start()
        t_err.start()
        
        try:
            proc.wait()
        except Exception:
            pass
        
        t_out.join()
        t_err.join()

        close_msg = {"type": "close", "code": proc.returncode}
        if request_id:
            close_msg["id"] = request_id
        sys.stdout.write(json.dumps(close_msg) + "\n")
        sys.stdout.flush()

    except FileNotFoundError:
        err_msg = {"type": "error", "data": f"Executable not found for shell: {shell_type}; try using another shell"}
        if request_id:
            err_msg["id"] = request_id
        sys.stdout.write(json.dumps(err_msg) + "\n")

        close_msg = {"type": "close", "code": 1}
        if request_id:
            close_msg["id"] = request_id
        sys.stdout.write(json.dumps(close_msg) + "\n")
        sys.stdout.flush()

    except Exception as e:
        err_msg = {"type": "error", "data": str(e)}
        if request_id:
            err_msg["id"] = request_id
        sys.stdout.write(json.dumps(err_msg) + "\n")
        sys.stdout.flush()

    finally:
        with process_lock:
            # clear the process reference on the session
            if getattr(session, 'process', None) is not None:
                session.process = None

class TerminalSession:
    def __init__(self, id, shell_type='cmd', cwd=None):
        self.id = id
        self.shell_type = shell_type
        self.cwd = cwd if cwd else os.getcwd()
        self.process = None
    def run(self, command):
        execute_command(self, command)

    def kill(self):
        # kill only this session's process
        kill_current_process(self.id)

    def destroy(self):
        self.kill()
        self.process = None
        
sessions = {}

def create_terminal_session(id, shell_type='cmd', cwd=None):
    if id in sessions:
        return sessions[id]
    session = TerminalSession(id, shell_type, cwd)
    sessions[id] = session
    return session
def get_terminal_session(id):
    return sessions.get(id, None)
def destroy_terminal_session(id):
    session = sessions.pop(id, None)
    if session:
        session.destroy()        

# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                   FUNCTION: MAIN (Main Input Loop)                         ║
# ╚════════════════════════════════════════════════════════════════════════════╝

def main():
    """
    Main loop that reads JSON requests from stdin and processes them.
    
    PROTOCOL:
        Input: JSON request with fields:
            - action: 'run' (execute) or 'kill' (interrupt)
            - command: command to execute (if action='run')
            - shell: shell type ('cmd', 'powershell', 'bash')
            - cwd: working directory (optional)
            - id: request ID for tracking (optional)
        
        Output: JSON responses with types:
            - start: process started {type, pid, id?}
            - stdout: standard output {type, data, id?}
            - stderr: error output {type, data, id?}
            - close: process finished {type, code, id?}
            - cwd_update: directory changed {type, data, id?}
            - error: execution error {type, data, id?}
    """
    # ═══════════════════════════════════════════════════════════════════════════════
    # MAIN LOOP: Read and process JSON requests indefinitely
    # ═══════════════════════════════════════════════════════════════════════════════
    
    while True:
        try:
            # ┌─ Read a line (JSON request) from stdin
            line = sys.stdin.readline()
            if not line: 
                # If stdin closes, exit loop
                break
            
            # ┌─ Parse JSON
            req = json.loads(line)
            
            # ┌─ Extract request fields
            action = req.get('action', 'run')
            req_id = req.get('id', None)
            # └─

            # ═══════════════════════════════════════════════════════════════════════════════
            # ACTION: KILL (Interrupt running process)
            # ═══════════════════════════════════════════════════════════════════════════════
            
            if action == 'kill':
                # kill only the session if id provided, otherwise kill all
                kill_current_process(req_id)
                continue
            # └─

            # ═══════════════════════════════════════════════════════════════════════════════
            # ACTION: RUN (Execute command)
            # ═══════════════════════════════════════════════════════════════════════════════
            
            if action == 'run':
                # ┌─ Extract request parameters
                cmd = req.get('command', '')
                raw_shell = str(req.get('shell', 'cmd')).strip().lower()
                shell = raw_shell if raw_shell in valid_shells else 'cmd'
                cwd_request = req.get('cwd', None)
                # session id fallback
                session_id = req_id or 'default'
                # ensure session exists (do not override existing session's cwd unless creating)
                session = create_terminal_session(session_id, shell, cwd_request)
                # └─

                # ┌─ SPECIAL HANDLING: 'cd' command (directory change)
                if cmd.strip().startswith('cd '):
                    # ┌─ Extract cd target
                    target = cmd.strip()[3:].strip()
                    try:
                        # expand ~ relative to user's home
                        if target == "~":
                            target = os.path.expanduser("~")

                        # resolve relative to session.cwd
                        base = session.cwd or os.getcwd()
                        potential_path = os.path.abspath(os.path.join(base, target))

                        if os.path.isdir(potential_path):
                            # update session cwd (session-scoped)
                            session.cwd = potential_path

                            resp = {"type": "cwd_update", "data": session.cwd}
                            if req_id:
                                resp["id"] = req_id
                            sys.stdout.write(json.dumps(resp) + "\n")

                            close = {"type": "close", "code": 0}
                            if req_id:
                                close["id"] = req_id
                            sys.stdout.write(json.dumps(close) + "\n")
                        else:
                            err = {"type": "stderr", "data": f"Path not found: {potential_path}\n"}
                            if req_id:
                                err["id"] = req_id
                            sys.stdout.write(json.dumps(err) + "\n")

                            close = {"type": "close", "code": 1}
                            if req_id:
                                close["id"] = req_id
                            sys.stdout.write(json.dumps(close) + "\n")
                    except Exception as e:
                        err = {"type": "stderr", "data": str(e)}
                        if req_id:
                            err["id"] = req_id
                        sys.stdout.write(json.dumps(err) + "\n")
                    sys.stdout.flush()
                    continue
                # └─

                # ┌─ Normal execution: run in session context
                session.run(cmd)
                # └─
            # └─

        except json.JSONDecodeError:
            # ┌─ Invalid JSON: notify and continue
            sys.stdout.write(
                json.dumps({
                    "type": "error", 
                    "data": "Invalid JSON Input"
                }) + "\n"
            )
            sys.stdout.flush()
            # └─
        except KeyboardInterrupt:
            # ┌─ Ctrl+C: exit program
            break
            # └─


# ╔════════════════════════════════════════════════════════════════════════════╗
# ║                        ENTRY POINT (Program Start)                         ║
# ╚════════════════════════════════════════════════════════════════════════════╝

if __name__ == "__main__":
    # ┌─ Execute main program loop
    main()
    # └─


