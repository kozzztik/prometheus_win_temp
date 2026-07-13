# Prometheus windows temperature exporter


TODO

Build
```bash
python -m nuitka --mode=standalone prometheus_win_temp\main.py --include-raw-dir=prometheus_win_temp\libre=libre --output-filename=prometheus_win_temp --output-folder-name=prometheus_win_temp --include-data-files=prometheus_win_temp\config.toml=config.toml
```
