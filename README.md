# AI Educational Assistant

## Descriere
Sistem inteligent de asistență educațională care simulează un profesor personal pentru elevi. Proiectul oferă suport în realizarea temelor și înțelegerea materiei prin intermediul inteligenței artificiale.

## Caracteristici Principale
- 🎓 Suport pentru multiple discipline școlare
- 🎵 Specializare pentru școli normale și de muzică
- 🤖 Integrare cu modele AI avansate
- 📚 Management inteligent al materialelor didactice
- ⚡ Sistem de cache pentru răspunsuri rapide
- 💰 Monitorizare costuri și utilizare tokens
- 🆓 Versiune gratuită disponibilă

## Tehnologii Utilizate
- Python
- Flask
- OpenAI API
- Railway (Deployment)
- Bubble.io (Frontend)
- Redis (Cache)

## Instalare
```bash
# Clonează repository-ul
git clone [URL_REPOSITORY]

# Instalează dependențele
pip install -r requirements.txt

# Configurează variabilele de mediu
cp .env.example .env
```

## Configurare
1. Adaugă cheile API în fișierul `.env`
2. Configurează parametrii în `config.py`
3. Ajustează setările pentru modelele AI în `ai_clients.py`

## Utilizare
```bash
# Pornește serverul în mod dezvoltare
python api_server.py

# Accesează aplicația la
http://localhost:5000
```

## API Endpoints
- `POST /api/intreaba` - Pune o întrebare profesorului virtual
- `GET /api/materii` - Obține lista materiilor disponibile
- `POST /api/feedback` - Trimite feedback pentru răspunsuri

## Structura Proiect
```
director_profesori/
├── api_server.py
├── main.py
├── main_free.py
├── config.py
├── ai_clients.py
├── requirements.txt
└── README.md
```

## Deployment
Proiectul este configurat pentru deployment pe Railway.
1. Conectează repository-ul la Railway
2. Configurează variabilele de mediu
3. Deployment automat la fiecare push

## Licență
[Tipul Licenței]

## Contact
[extasssy@gmail.com - Ordean Eduard Gabi]

## Status
🚀 În dezvoltare activă

## Contribuții
Contribuțiile sunt binevenite! Te rugăm să citești [CONTRIBUTING.md] pentru detalii despre procesul de submitere a pull request-urilor.