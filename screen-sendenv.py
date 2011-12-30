#!/usr/bin/env python

import plac
import logging
import sys
import os
import os.path
import subprocess

# This doesn't just open /dev/null directly because tmux hangs when
# its output is redirected directly to a file instead of piped through
# another process. Python is used here because it is guaranteed to be
# available if this script is already running.
devnull_cmd = ['python', '-c', 'import sys; import os; open(os.devnull, "w").writelines(sys.stdin)']
devnull = subprocess.Popen(devnull_cmd, stdin=subprocess.PIPE).stdin

import abc

class EnvSender(object):
    __metaclass__ = abc.ABCMeta
    def __init__(self, socket=None, path=None, **kwargs):
        self.socket = socket
        self.path = path or self.default_path
        self.handle_kwargs(kwargs)
        self.verify_connection()

    def send_cmd(self, cmd):
        """Send cmd to specified process. cmd is a list of strings."""
        assert cmd is not None
        cmd = self.command_prelude() + cmd + self.command_postlude()
        logging.debug("Running %s" % cmd)
        subprocess.check_call(cmd, stdout=devnull, stderr=devnull)
    def verify_connection(self):
        """Verify that the specified session is accessible."""
        try:
            self.send_cmd(self.test_command())
        except subprocess.CalledProcessError:
            raise Exception("Could not connect to specified session")
    def send_variable(self, name, value):
        """Set environment variable NAME to VALUE in session."""
        self.send_cmd(self.sendenv_command(name, value))

    def handle_kwargs(self, kwargs):
        """Handle additional init arguments.

        This can be overridden by subclasses to handle (and require
        the presence of) specific keyword arguments."""
        pass

    # These functions must be implemented by subclasses (except for
    # command_postlude, which is optional)
    @abc.abstractproperty
    def default_path(self):
        """Default path to multiplexer executable."""
        raise NotImplementedError()

    @abc.abstractmethod
    def command_prelude(self):
        """Return the full prelude required to send a command.

        This should use both self.path and self.socket"""
        raise NotImplementedError()
    def command_postlude(self):
        """Only implement this if post-arguments are required after the command."""
        return []
    @abc.abstractmethod
    def test_command(self):
        """Return a command that is a no-op for the multiplexer.

        It can produce output, which will be ignored. It will be used
        to test whether the specified socket and path are working
        properly."""
        raise NotImplementedError()
    @abc.abstractmethod
    def sendenv_command(name, value):
        """Return the multiplexer command to set an environment variable.

        If value is None, return the command to unset the variable."""
        raise NotImplementedError()


class ScreenEnvSender(EnvSender):
    def socket_argspec(self):
        return [ "-S", self.socket ] if self.socket else []
    def command_prelude(self):
        return [ self.path ] + self.socket_argspec() + [ "-X" ]
    def test_command(self):
        return [ "echo", "" ]
    def sendenv_command(self, name, value):
        if value is None:
            cmd = [ "unsetenv", name ]
        else:
            cmd = [ "setenv", name, value ]
        return cmd
    @property
    def default_path(self):
        return "screen"

class TmuxEnvSender(EnvSender):
    def handle_kwargs(self, kwargs):
        try:
            self.session = kwargs['session']
        except KeyError:
            self.session = None
    def session_argspec(self):
        if not self.session:
            return []
        else:
            return [ "-t", str(self.session) ]
    def socket_argspec(self):
        if not self.socket:
            return []
        socket = str(self.socket)
        # Seeing a path separator means this is a path
        if socket.find(os.path.sep) != -1:
            return [ "-S", socket ]
        else:
            return [ "-L", socket ]
    def command_prelude(self):
        return [ self.path ] + self.socket_argspec()
    def test_command(self):
        return [ "list-windows" ] + self.session_argspec()
    def sendenv_command(self, name, value):
        if value is None:
            cmd = [ "setenv" ] + self.session_argspec() + [ "-u", name ]
        else:
            cmd = [ "setenv" ] + self.session_argspec() + [ name, value ]
        return cmd
    @property
    def default_path(self):
        return "tmux"

session_types = {
    'screen' : ScreenEnvSender,
    'tmux' : TmuxEnvSender,
}

@plac.annotations(
    # arg=(helptext, kind, abbrev, type, choices, metavar)
    # [INSERT ARGS HERE]
    quiet=("Do not print informational messages.", "flag", "q"),
    verbose=("Print debug messages that are probably only useful if something is going wrong.", "flag", "v"),
    session_type=("Which terminal multiplexer to use. Currently supported are 'screen' and 'tmux'.", "option", "t", str, session_types.keys()),
    program_path=("Path to multiplexer executable. Only required if not in $PATH", "option", "p", str, None, 'PATH'),
    socket=("Socket name", "option", "S", str, None, "SOCKNAME"),
    session=("Session number. Only meaningful for tmux.", "option", "s", int, None, 'NUMBER'),
    vars=("Variables to send to multiplexer. If no value is specified for a variable, its value will be taken from the current environment.", "positional", None, str, None, "VAR[=VALUE]"),
    )
def main(session_type="screen", session=None,
         socket=None, program_path=None,
         quiet=False, verbose=False,
         *vars):
    """Update environment variables in a running terminal multiplexer.

Each argument is a variable whose value in the current environment
should be sent to the screen process. You can override the value to
send for each variable by giving a value after an equals sign.

Note that updated environment variables will only take effect for
newly-created windows inside the multiplexer."""
    if quiet:
        logging.basicConfig(level=logging.WARN)
    elif verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    sender_class = session_types[session_type]
    sender = sender_class(path=program_path, socket=socket, session=session)
    for var in vars:
        if var.find("=") != -1:
            var, value = var.split("=", 1)
        else:
            value = os.getenv(var)
        logging.debug("Sending %s=%s" % (var, value))
        sender.send_variable(var, value)

# Entry point
def plac_call_main():
    return plac.call(main)

if __name__=="__main__":
    plac_call_main()
