# Grape - Django Port

Clone di Miiverse in Django Python, portato da PHP (ariankordi/grape).

## Struttura

```
grape_django/
├── manage.py
├── requirements.txt
├── grape_project/          # Configurazione Django
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── grape/                  # App principale
│   ├── models.py           # Modelli DB (identici allo schema PHP)
│   ├── helpers.py          # Funzioni helper (equivalenti a grplib-php)
│   ├── middleware.py       # Rilevamento WiiU/offdevice
│   ├── context_processors.py
│   ├── urls_portal.py      # URL per interfaccia WiiU (/)
│   ├── urls_offdevice.py   # URL per interfaccia web (/web/)
│   ├── views/
│   │   ├── auth_views.py   # Login, logout, registrazione
│   │   ├── portal_views.py # Interfaccia WiiU
│   │   ├── offdevice_views.py # Interfaccia web /web/
│   │   └── error_views.py  # 404, 500
│   └── templatetags/
│       └── grape_tags.py   # Tag template personalizzati
├── templates/
│   ├── portal/             # Template interfaccia WiiU
│   └── offdevice/          # Template interfaccia web
└── static/                 # Copia qui i file Static/ dal PHP originale
```

## Installazione

### 1. Prerequisiti

```bash
pip install -r requirements.txt
```

### 2. Database MySQL

Crea il database MySQL con lo stesso schema dell'originale grape PHP:

```sql
CREATE DATABASE grape CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Poi esegui le migration Django:
```bash
python manage.py makemigrations grape
python manage.py migrate
```

### 3. File statici

Copia la cartella `Static/` dal progetto PHP originale nella cartella `static/` del progetto Django:
```bash
cp -r /path/to/grape-original/Static/* static/
```

### 4. Configurazione

Modifica `grape_project/settings.py`:
- `SECRET_KEY` → chiave segreta casuale lunga
- `DATABASES` → credenziali MySQL
- `DEBUG` → `False` in produzione
- `ALLOWED_HOSTS` → il tuo dominio

### 5. Avvio

```bash
# Sviluppo
python manage.py runserver

# Produzione (con gunicorn)
gunicorn grape_project.wsgi:application --bind 0.0.0.0:8000
```

## Come funziona il routing

- **`/`** → Interfaccia WiiU (portal-grp.css / portal-grp_offdevice.css)
  - Detecta automaticamente Wii U tramite User-Agent `miiverse`
  - Su browser normale usa il CSS offdevice
- **`/web/`** → Sempre interfaccia offdevice (offdevice.css)

## Differenze rispetto al PHP originale

1. **Email rimossa** — La libreria PearMail è stata rimossa. Nessun sistema di conferma email.
2. **Password** — Usa Django's `make_password` (bcrypt), compatibile con il PHP bcrypt.
3. **PJAX** — I template supportano le richieste PJAX tramite `X-PJAX` header per le transizioni smooth.
4. **Empathy (Yeah)** — Nell'interfaccia offdevice usa form HTML normale invece di AJAX per massima compatibilità.
5. **3DS** — La cartella 3DS era vuota, non implementata.
6. **Admin panel** — Usa l'admin Django built-in: `/admin/`

## Bug fixati dal PHP

- Iniezione SQL corretta → uso di ORM Django con parametri sicuri
- Race condition nelle empathy → `get_or_create` atomico
- Errori silenti nel PHP → eccezioni Django esplicite
- `hidden_resp` check incompleto → corretto in tutti i template

## Aggiungere admin Django

```bash
python manage.py createsuperuser
```

Poi registra i modelli nell'admin in `grape/admin.py`.
