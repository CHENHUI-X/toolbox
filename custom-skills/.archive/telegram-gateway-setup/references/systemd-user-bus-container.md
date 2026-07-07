# Systemd User Bus Failure in Container Environments

Reproduced from a GCP container environment running Hermes Agent.

## Error

```
$ hermes gateway install
Start the gateway now after installing the service? [Y/n]: Y
Start the gateway automatically on login/boot with systemd? [Y/n]: Y
Installing user systemd service to: /root/.config/systemd/user/hermes-gateway.service
Failed to connect to bus: No medium found

Traceback (most recent call last):
  File ".../hermes_cli/main.py", line 1820, in cmd_gateway
    gateway_command(args)
  File ".../hermes_cli/gateway.py", line 5135, in gateway_command
    return _gateway_command_inner(args)
  File ".../hermes_cli/gateway.py", line 5188, in _gateway_command_inner
    systemd_install(
  File ".../hermes_cli/gateway.py", line 2503, in systemd_install
    _run_systemctl(["daemon-reload"], system=system, check=True, timeout=30)
  File ".../hermes_cli/gateway.py", line 1571, in _run_systemctl
    return subprocess.run(_systemctl_cmd(system) + args, **kwargs)
subprocess.CalledProcessError: Command '['systemctl', '--user', 'daemon-reload']' returned non-zero exit status 1.
```

## Environment Detection

```bash
# Check if this is a container
cat /proc/1/cgroup
# → 0::/init.scope  (container)

# Check init system
cat /proc/1/cmdline | tr '\0' ' '
# → /sbin/init

# Check systemd user bus
systemctl --user status
# → Failed to connect to bus: No medium found

# Check if systemd user manager exists
ps aux | grep "systemd.*--user"
# → Only shows for OTHER users (e.g. didi:1002), NOT for root

# Check runtime dirs
ls /run/user/
# → drwx------  3 didi didi 100 May 25 08:45 1002
# → No /run/user/0 for root

# Check dbus socket
ls /run/dbus/
# → containers  system_bus_socket
# → No user bus socket

# System-level systemd is available
sudo systemctl status
# → works fine
```

## Resolution

Used a system-level (not user-level) systemd unit file at `/etc/systemd/system/hermes-gateway.service` with `User=root`.
