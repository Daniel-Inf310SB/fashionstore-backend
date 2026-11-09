# FashionStore — API y worker separados

## Desarrollo (dos terminales, entorno virtual activado)

```powershell
python -m uvicorn app.main:app --reload
```

```powershell
python -m app.worker
```

La API ya no inicia trabajos programados. El worker ejecuta las tareas configuradas de expiración, push Firebase, campañas y conciliación Stripe. Se conectan a la misma base PostgreSQL. Una segunda instancia del worker con la misma base de datos se rechaza por un bloqueo advisory de sesión. El worker no tiene puerto HTTP público.

## Ubuntu / systemd

Ejemplos orientativos; sustituye las rutas y crea el usuario `fashionstore`. Mantén `.env` y claves privadas fuera del paquete público.

`/etc/systemd/system/fashionstore-api.service`:

```ini
[Unit]
Description=FashionStore FastAPI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=fashionstore
WorkingDirectory=/opt/fashionstore
ExecStart=/opt/fashionstore/.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

`/etc/systemd/system/fashionstore-worker.service`:

```ini
[Unit]
Description=FashionStore worker de tareas programadas
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=fashionstore
WorkingDirectory=/opt/fashionstore
ExecStart=/opt/fashionstore/.venv/bin/python -m app.worker
Restart=on-failure
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now fashionstore-api fashionstore-worker
sudo systemctl status fashionstore-api fashionstore-worker
sudo journalctl -u fashionstore-worker -f
```

Nginx ofrece HTTPS delante de la API. No expongas el worker a Internet. Si el worker pierde conexión con PostgreSQL, se detiene para no seguir procesando sin bloqueo y systemd lo reinicia. Un bloqueo exclusivo **no** reemplaza las validaciones transaccionales de pagos, existencias y entregas. Los intervalos perdidos durante un apagado no se recuperan automáticamente en todos los casos.

## Verificaciones

```powershell
python -m pytest tests/test_worker_separation.py -q
python -m compileall -q app
```

Probar además con PostgreSQL real: arrancar un worker, intentar un segundo (debe fallar), detener el primero y comprobar que se puede iniciar otro.

**Conservar:** `app/main.py`, `app/jobs/*.py`, `app/core/config.py`, `app/database/session.py`. Solo se retiró el scheduler de `app/main.py`. No eliminar los jobs: el worker los importa.
