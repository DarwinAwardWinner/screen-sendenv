#!/usr/bin/env python

import plac
import logging
import sys
import os
import subprocess

def socket_spec(socket=None):
    return [ "-S", socket ] if socket else []

devnull = open(os.devnull, "w")

def verify_socket(socket=None, screenpath="screen"):
    cmd = [ screenpath ] + socket_spec(socket) + [ "-X", "echo", "" ]
    logging.debug("Checking socket with %s" % cmd)
    try:
        subprocess.check_call(cmd, stdout=devnull, stderr=devnull)
    except subprocess.CalledProcessError:
        raise ValueError("Invalid socket")
    logging.debug("Socket check succeeded")

def sendenv_command(name, value=None, socket=None, screenpath="screen"):
    if not (name and str(name)):
        raise ValueError("Name must be a nonempty string")
    if value is None:
        value = os.getenv(name)
    if value is None:
        screen_cmd = [ "unsetenv", name ]
    else:
        screen_cmd = [ "setenv", name, value ]
    shell_cmd = [ screenpath ] + socket_spec(socket) + [ "-X" ] + screen_cmd
    return shell_cmd

def sendenv(*args, **kwargs):
    cmd = sendenv_command(*args, **kwargs)
    logging.debug("Sending envvar with %s" % cmd)
    subprocess.check_call(cmd)

@plac.annotations(
    # arg=(helptext, kind, abbrev, type, choices, metavar)
    # [INSERT ARGS HERE]
    quiet=("Do not print informational messages.", "flag", "q"),
    verbose=("Print debug messages that are probably only useful if something is going wrong.", "flag", "v"),
    screenpath=("Path to screen executable", "option", "p"),
    socket=("Screen socket name", "option", "S", str, None, "SOCKNAME"),
    vars=("Variables to send to screen process", "positional", None, None, None, "VAR[=VALUE]"),
    )
def main(socket=None, screenpath="screen",
         quiet=False, verbose=False,
         *vars):
    """Update environment variables in a running screen process.

Each argument is a variable whose value in the current environment
should be sent to the screen process. You can override the value to
send for each variable by giving a value after an equals sign."""
    if quiet:
        logging.basicConfig(level=logging.WARN)
    elif verbose:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)
    verify_socket(socket)
    for var in vars:
        if var.find("=") != -1:
            var, value = var.split("=", 1)
        else:
            value = os.getenv(var)
        logging.debug("Sending %s=%s" % (var, value))
        sendenv(var, value, socket=socket, screenpath=screenpath)

# Entry point
def plac_call_main():
    return plac.call(main)

if __name__=="__main__":
    plac_call_main()
