"""Sinal vermelho se não houve nenhuma coleta válida nas últimas 30 horas."""
import sys
from datetime import datetime, timezone, timedelta
from promoradar.storage import read_series
runs = read_series('runs')
ok = [r for r in runs if r.get('status') in ('ok','partial') and r.get('observations_count',0)>0]
if not ok:
    sys.exit('ALERTA: Nenhuma coleta real bem-sucedida registrada ainda.')
last = max(datetime.fromisoformat(r['started_at']) for r in ok)
if datetime.now(timezone.utc)-last > timedelta(hours=30):
    sys.exit(f'ALERTA: Última coleta válida em {last.isoformat()}, há mais de 30 horas.')
print(f'OK: Última coleta válida em {last.isoformat()}')
