# Prometheus windows temperature exporter

Adds support of temperature metrics to prometheus [windows-exporter](https://github.com/prometheus-community/windows_exporter/tree/master), provided by [Libre Hardware Monitor](https://github.com/LibreHardwareMonitor/LibreHardwareMonitor) on Windows.

Simple to install and use.

### Install

You should have [windows-exporter](https://github.com/prometheus-community/windows_exporter/tree/master) installed.

Enable files import in `windows-exporter`:
```powershell
notepad "C:\Program Files\Prometheus\windows_exporter\config.yml
```
For default installation it should be empty. Replace with:
```yaml
collectors:
  enabled: cpu,logical_disk,memory,net,os,physical_disk,service,system,textfile
```

Extract files of `prometheus-windows-exporter` from archive somewhere like `C:\Program Files\prometheus_win_temp`.

Edit config file for your taste:
```powershell
notepad "C:\Program Files\prometheus_win_temp\config.toml"
```
For example add sentry dsn for exceptions logging.

```toml
file_path = "C:\\Program Files\\windows_exporter\\textfile_inputs\\temp.prom"
period = 5
sensor_types = ["Temperature", "SmallData", "Load"]

[sentry]
dsn = "..."
environment = "dev"
```
Install it as service (**run with administrator privileges**) and run:
```commandline
"C:\Program Files\prometheus_win_temp\service.exe" --startup auto install
"C:\Program Files\prometheus_win_temp\service.exe" start
```

Enjoy!

### Build (for developers)
```bash
pip install py2exe
python3 build.py
xcopy dist "C:\Program Files\prometheus_win_temp" /E /Y
"C:\Program Files\prometheus_win_temp\service.exe" --startup auto install
```
