from pathlib import Path
from datetime import datetime, timezone
import json
p=Path('data.json')
d=json.loads(p.read_text())
d['last_checked']=datetime.now(timezone.utc).strftime('%d %b %Y %H:%M UTC')
d['changed_count']=0
p.write_text(json.dumps(d,indent=2)+'\n')
h=Path('data/history.json')
h.parent.mkdir(exist_ok=True)
a=json.loads(h.read_text()) if h.exists() else []
a.append({'checked_at':d['last_checked'],'changed_count':0})
h.write_text(json.dumps(a[-1000:],indent=2)+'\n')
