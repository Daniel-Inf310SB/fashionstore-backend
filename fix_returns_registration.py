"""Move return router registration to the normal router group in app/main.py.
Run in FashionStore backend root. Makes a backup before changing anything.
"""
from pathlib import Path
import ast
import shutil
from datetime import datetime

path=Path('app/main.py')
if not path.is_file():
    raise SystemExit('Ejecuta el script desde la raiz de fashionstore_api (falta app/main.py)')
source=path.read_text(encoding='utf-8')
old='from app.api.routes.returns import router as returns_router\napp.include_router(returns_router)'
if source.count(old)!=1:
    raise SystemExit('No se encontro exactamente una declaracion original; no se hicieron cambios.')
# existing project route: platform_tenants_router. Insert immediately ahead so route registration is not at tail.
anchor='app.include_router(platform_tenants_router)'
if source.count(anchor)!=1:
    raise SystemExit('Ancla del router principal ambigua/no encontrada; no se hicieron cambios.')
fixed=source.replace(old,'',1).replace(anchor,old+'\n'+anchor,1)
ast.parse(fixed, filename=str(path))
backup=path.with_name('main.py.bak_returns_'+datetime.now().strftime('%Y%m%d_%H%M%S'))
shutil.copy2(path,backup)
path.write_text(fixed,encoding='utf-8')
print('Router de devoluciones reubicado. Respaldo:',backup)
print('Ahora ejecuta la verificacion de rutas.')
