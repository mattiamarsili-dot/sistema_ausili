# Contesto: UI Design — Sistema Ausili

Sessione focalizzata sul miglioramento dell'interfaccia web.
Progetto Flask su Railway: https://web-production-d6861.up.railway.app

---

## Stack attuale

- **Bootstrap 5.3.2** (CDN) — layout, form, card, modal, badge, alert
- **Bootstrap Icons 1.11.3** (CDN) — tutte le icone (prefisso `bi-`)
- **JavaScript vanilla** — nessun jQuery, nessuna libreria esterna
- **Nessun file CSS/JS custom** — `static/css/` e `static/js/` sono vuoti
- Tutto il CSS è inline in `<style>` dentro `base.html` (~135 righe)

---

## File chiave

| File | Descrizione |
|---|---|
| `templates/base.html` | Layout base: sidebar, navbar mobile, bottom nav, flash messages |
| `templates/index.html` | Dashboard con KPI e ultime pratiche |
| `templates/clienti.html` | Lista clienti (tabella + card view) |
| `templates/cliente_form.html` | Form crea/modifica cliente |
| `templates/pratiche.html` | Lista pratiche con filtri |
| `templates/pratica_form.html` | Form pratica + voci + compilazione PDF (più complesso) |
| `templates/templates.html` | Gallery template PDF |
| `templates/template_form.html` | Configurazione mapping campi PDF |
| `templates/nomenclatore.html` | Catalogo voci ISO (modal inline) |
| `templates/testi_prescrizione.html` | Testi prescrizione per ausilio |
| `templates/importa.html` | Browser file + analisi con Claude AI |
| `static/` | Cartella vuota — aggiungere qui CSS/JS custom |

---

## Design system attuale

### Colori
```css
/* Sidebar */
background: #1a2540;          /* blu scuro */
accent attivo: #4db8ff;       /* blu chiaro */
text sidebar: rgba(255,255,255,0.75);

/* Accent generale */
--bs-primary: Bootstrap default (#0d6efd)

/* Badge stato pratiche */
Aperta    → badge bg-primary
In corso  → badge bg-warning text-dark
Completata → badge bg-success
Chiusa    → badge bg-secondary
In attesa → badge bg-danger
```

### Layout
- **Sidebar desktop**: 220px fissa a sinistra, sempre visibile
- **Main content**: margin-left 220px, padding 1.5rem
- **Navbar mobile**: 56px fissa in alto (hamburger + logo)
- **Bottom nav mobile**: 58px fisso in basso, 6 icone principali
- **Breakpoint mobile**: 768px

### Componenti presenti
- **Stat cards** (dashboard): gradient colorati con KPI
- **Tabelle responsive** con hover + action buttons inline
- **Card view alternativa** (clienti/pratiche) via `?vista=card`
- **Filtri e barre ricerca** con select e input testo
- **Modal Bootstrap** (nomenclatore, airtable)
- **Flash messages** dismissibili (success/danger/warning)
- **Badge stato** pratiche e template
- **Breadcrumb** navigazione Drive
- **File browser** con icone per tipo file

---

## Pagine e URL

| Pagina | URL | Note |
|---|---|---|
| Dashboard | `/` | KPI + ultime pratiche/clienti |
| Clienti | `/clienti` | Lista + filtro + vista card |
| Nuovo/modifica cliente | `/clienti/nuovo`, `/clienti/<id>` | Form con tutti i campi |
| Pratiche | `/pratiche` | Lista + filtri stato/centro/ausilio |
| Nuova/modifica pratica | `/pratiche/nuova`, `/pratiche/<id>` | Form + voci + PDF |
| Template PDF | `/templates` | Gallery card |
| Configura template | `/templates/<id>` | Mapping campi PDF |
| Nomenclatore | `/nomenclatore` | Tabella voci ISO + modal |
| Testi prescrizione | `/templates/testi-prescrizione` | Testi per ausilio |
| Chiavi custom | `/templates/chiavi` | Mapping chiavi aggiuntive |
| Importa documenti | `/importa` | Browser file + AI extraction |
| Importa Airtable | `/importa-airtable` | Import clienti/pratiche |

---

## Architettura template

Tutti i template estendono `base.html`:
```html
{% extends "base.html" %}
{% block title %}Titolo pagina{% endblock %}
{% block content %}
  <!-- contenuto pagina -->
{% endblock %}
```

`base.html` fornisce:
- `<head>` con Bootstrap CDN
- Sidebar + nav mobile
- `{% block content %}` per il contenuto
- Flash messages automatici
- JS sidebar toggle

---

## Note tecniche

- I **file statici custom** vanno in `static/css/` o `static/js/` e inclusi in `base.html`
- Per aggiungere un file CSS custom: `<link rel="stylesheet" href="{{ url_for('static', filename='css/custom.css') }}">`
- Il CSS inline attuale in `base.html` può essere estratto in `static/css/main.css`
- Le route Flask sono tutte in `app.py` (752 righe)
- I dati alle pagine arrivano via `render_template()` con variabili Jinja2
- API JSON disponibili per fetch dinamico (voci pratica, varianti testo, stato airtable)

---

## Aree da migliorare (da valutare in questa sessione)

- [ ] Estrarre CSS inline da `base.html` in file separato `static/css/main.css`
- [ ] Migliorare la pagina pratiche (filtri, ordinamento, informazioni mostrate)
- [ ] UX form pratica (sezione voci e PDF più chiara)
- [ ] Dashboard più informativa (grafici, stati pratiche)
- [ ] Responsive migliorato per tablet
- [ ] Feedback visivo compilazione PDF (loading state)
- [ ] Migliorare la lista template PDF (anteprima, info mapping)

---

## Come avviare in locale

```bash
cd "/Users/mattiamarsili/Cloude code Lavoro/sistema_ausili"
python3 app.py
# oppure
bash avvia.sh
```
App disponibile su http://localhost:5000
