This is a script to inject environment variables into an
already-running screen session. An example use case would be to set a
new value for DISPLAY when you start a new X session, so that you can
still start X11 programs from a shell in your screen session.

Note that any new environment variables would only take effect for
newly-spawned windows in screen. For tmux you could get creative with
a bash function that reads the output of `tmux showenv` and injects
the environment variables into an existing shell, but you'll still
have to do it manually.

## Example usage

To send the current value of `$DISPLAY`:

    $ screen-sendenv.py DISPLAY
    
To send a specific value of `$DISPLAY`:

    $ screen-sendenv.py DISPLAY=":2"
