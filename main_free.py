"""
Versiunea gratuită a sistemului educational AI
Limitată la 10 utilizatori, folosește DeepSeek și Claude
"""

import os
import openai
from dotenv import load_dotenv
import json
import logging
from main import *
from typing import Dict, List, Optional
from config import Config, token_monitor
from ai_clients import ai_client_manager
import time

# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sistem_educational_free.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

load_dotenv()
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

class ConfigurariProfesorFree:
    """
    Configurări optimizate pentru versiunea gratuită
    """
    def __init__(self, temperature=0.7, max_tokens=500, model="gpt-3.5-turbo", 
                 personalitate="prietenos", stil_predare="simplu"):
        self.temperature = temperature
        self.max_tokens = max_tokens  # Redus de la 2584 la 500
        self.model = model  # Doar GPT-3.5-turbo pentru free
        self.personalitate = personalitate
        self.stil_predare = stil_predare
        self.nivel_pacienta = "ridicat"
        self.stil_comunicare = "adaptat_varstei"

class ProfesorFree:
    """
    Versiunea gratuită a profesorului - optimizată pentru costuri
    """
    def __init__(self, nume, materie, clasa, scoala, configurari=None):
        self.nume = nume
        self.materie = materie
        self.clasa = clasa
        self.scoala = scoala
        self.configurari = configurari or ConfigurariProfesorFree()
        self.istoric_conversatii = []
        self.limite_zilnice = {
            "intrebari_maxime": 5,  # Max 5 întrebări pe zi per utilizator
            "intrebari_folosite": 0,
            "ultima_resetare": time.strftime("%Y-%m-%d")
        }

    def verifica_limite_zilnice(self, user_id="default"):
        """Verifică limitele zilnice pentru utilizatorul gratuit"""
        data_curenta = time.strftime("%Y-%m-%d")
        
        # Resetează contorul dacă e o zi nouă
        if self.limite_zilnice["ultima_resetare"] != data_curenta:
            self.limite_zilnice["intrebari_folosite"] = 0
            self.limite_zilnice["ultima_resetare"] = data_curenta
        
        if self.limite_zilnice["intrebari_folosite"] >= self.limite_zilnice["intrebari_maxime"]:
            return False, f"Ai atins limita de {self.limite_zilnice['intrebari_maxime']} întrebări pe zi. Încearcă mâine sau upgrade la versiunea Pro!"
        
        return True, ""

    def obtine_prompt_simplu(self, intrebare):
        """Prompt optimizat pentru versiunea gratuită - mai scurt și eficient"""
        prompt_clasa = {
            0: "Explică simplu pentru copii de 5-6 ani",
            1: "Explică pentru copii de 6-7 ani",
            2: "Explică pentru copii de 7-8 ani", 
            3: "Explică pentru copii de 8-9 ani",
            4: "Explică pentru copii de 9-10 ani"
        }

        prompt = f"""Ești {self.nume}, profesor de {self.materie} pentru clasa {self.clasa}.
{prompt_clasa.get(self.clasa, "Adaptează răspunsul pentru vârsta copilului")}.

Întrebare: "{intrebare}"

Răspunde scurt, clar și prietenos. Ajută copilul să înțeleagă, nu să copieze răspunsul."""

        return prompt

    def raspunde_intrebare(self, intrebare, user_id="default"):
        """Răspunde la întrebare cu limitări pentru versiunea gratuită"""
        
        # Verifică limitele zilnice
        poate_raspunde, mesaj_eroare = self.verifica_limite_zilnice(user_id)
        if not poate_raspunde:
            return mesaj_eroare

        prompt = self.obtine_prompt_simplu(intrebare)
        
        try:
            # Folosește doar GPT-3.5-turbo pentru free tier
            result = ai_client_manager.get_ai_response(
                prompt=prompt,
                subject=self.materie,
                user_id=user_id,
                is_free_tier=True,
                max_tokens=self.configurari.max_tokens,
                temperature=self.configurari.temperature
            )
            
            raspuns = result["content"]
            
            # Incrementează contorul de întrebări
            self.limite_zilnice["intrebari_folosite"] += 1
            
            # Salvează conversația
            self.istoric_conversatii.append({
                "intrebare": intrebare,
                "raspuns": raspuns,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "tokens_used": result["tokens_used"],
                "user_id": user_id
            })
            
            # Adaugă mesaj promotional la sfârșitul răspunsului
            intrebari_ramase = self.limite_zilnice["intrebari_maxime"] - self.limite_zilnice["intrebari_folosite"]
            if intrebari_ramase > 0:
                raspuns += f"\n\n💡 Îți mai rămân {intrebari_ramase} întrebări astăzi. Pentru întrebări nelimitate, upgrade la Pro!"
            else:
                raspuns += f"\n\n🚀 Ai folosit toate întrebările gratuite de astăzi! Upgrade la Pro pentru acces nelimitat și profesori specializați!"
            
            return raspuns
            
        except Exception as e:
            error_msg = f"Eroare: {str(e)}"
            logger.error(error_msg)
            return error_msg

def creeaza_configurari_profesor_free(materie, clasa):
    """Configurări simplificate pentru versiunea gratuită"""
    
    # Configurări de bază pentru toate materiile în versiunea free
    configurari_base = {
        "temperature": 0.7,
        "max_tokens": 400,  # Redus pentru a economisi
        "model": "gpt-3.5-turbo",  # Doar modelul cel mai ieftin
        "personalitate": "prietenos",
        "stil_predare": "simplu"
    }
    
    # Ajustări minore pe materii
    if materie in ["Matematica", "Matematica_si_Explorarea_mediului"]:
        configurari_base["temperature"] = 0.5  # Mai puțin creativ pentru matematică
        configurari_base["max_tokens"] = 350
    elif materie in ["Comunicare_in_Limba_Romana", "Limba_si_Literatura_Romana"]:
        configurari_base["temperature"] = 0.8  # Puțin mai creativ pentru română
        configurari_base["max_tokens"] = 450
    
    return ConfigurariProfesorFree(**configurari_base)

class SistemEducationalFree:
    """Sistem educational pentru varianta gratuită"""

    def __init__(self):
        self.profesori_disponibili = self.creeaza_profesori_free()
        self.scoala_normala, self.scoala_muzica = creeaza_structura_educationala()
        self.utilizatori_activi = {}
        self.limite_globale = {
            "utilizatori_maximi": 10,
            "intrebari_totale_pe_zi": 50
        }

    def creeaza_profesori_free(self):
        """Creează doar profesorii esențiali pentru versiunea gratuită"""
        profesori = {}
        
        # Doar materiile principale pentru fiecare clasă
        materii_esentiale = {
            0: [("Comunicare_in_Limba_Romana", "Prof_Ion_Creanga"),
                ("Matematica_si_Explorarea_mediului", "Prof_Pitagora")],
            1: [("Comunicare_in_Limba_Romana", "Prof_Ion_Creanga"),
                ("Matematica_si_Explorarea_mediului", "Prof_Pitagora")],
            2: [("Comunicare_in_Limba_Romana", "Prof_Ion_Creanga"),
                ("Matematica_si_Explorarea_mediului", "Prof_Pitagora")],
            3: [("Limba_si_Literatura_Romana", "Prof_Mihai_Eminescu"),
                ("Matematica", "Prof_Euclid")],
            4: [("Limba_si_Literatura_Romana", "Prof_Mihai_Eminescu"),
                ("Matematica", "Prof_Euclid")]
        }
        
        for clasa, materii in materii_esentiale.items():
            profesori[clasa] = {}
            for materie, nume_profesor in materii:
                configurari = creeaza_configurari_profesor_free(materie, clasa)
                profesor = ProfesorFree(nume_profesor, materie, clasa, "Scoala_Gratuita", configurari)
                profesori[clasa][materie] = profesor
        
        return profesori

    def alege_profesor_simplu(self, intrebare, clasa):
        """Alegere simplă a profesorului bazată pe cuvinte cheie"""
        if clasa not in self.profesori_disponibili:
            return None
        
        intrebare_lower = intrebare.lower()
        
        # Cuvinte cheie pentru matematică
        cuvinte_matematica = ["calcul", "număr", "plus", "minus", "înmulți", "împart", "problemă", "exercițiu", "egal"]
        
        # Verifică dacă întrebarea e despre matematică
        if any(cuvant in intrebare_lower for cuvant in cuvinte_matematica):
            materie_key = "Matematica" if clasa >= 3 else "Matematica_si_Explorarea_mediului"
            if materie_key in self.profesori_disponibili[clasa]:
                return self.profesori_disponibili[clasa][materie_key]
        
        # Altfel, returnează profesorul de română
        materie_romana = "Limba_si_Literatura_Romana" if clasa >= 3 else "Comunicare_in_Limba_Romana"
        if materie_romana in self.profesori_disponibili[clasa]:
            return self.profesori_disponibili[clasa][materie_romana]
        
        # Fallback - primul profesor disponibil
        return list(self.profesori_disponibili[clasa].values())[0]

    def poate_adauga_utilizator(self, user_id):
        """Verifică dacă se poate adăuga un nou utilizator"""
        if user_id in self.utilizatori_activi:
            return True, "Utilizator existent"
        
        if len(self.utilizatori_activi) >= self.max_utilizatori:
            return False, f"Limita de {self.max_utilizatori} utilizatori a fost atinsă"
        
        return True, "OK"
    
    def adauga_utilizator(self, user_id):
        """Adaugă un utilizator nou"""
        poate, mesaj = self.poate_adauga_utilizator(user_id)
        if poate:
            self.utilizatori_activi.add(user_id)
            return True, mesaj
        return False, mesaj
    
    def pune_intrebare(self, user_id, intrebare, scoala_nume, clasa):
        """Pune o întrebare în sistemul gratuit"""
        
        # Verifică utilizatorul
        poate, mesaj = self.adauga_utilizator(user_id)
        if not poate:
            return {"error": mesaj}
        
        # Selectează școala
        if "Normala" in scoala_nume:
            scoala = self.scoala_normala
        else:
            scoala = self.scoala_muzica
        
        # Directorul alege profesorul
        director = scoala.directori[0]
        profesor_ales = director.alege_profesor_pentru_intrebare(intrebare, clasa)
        
        if not profesor_ales:
            return {"error": "Nu s-a găsit un profesor potrivit"}
        
        try:
            # Obține răspunsul (forțează varianta gratuită)
            raspuns = profesor_ales.raspunde_intrebare(
                intrebare, 
                user_id=user_id, 
                is_free_tier=True
            )
            
            # Statistici
            stats = token_monitor.get_stats()
            
            return {
                "raspuns": raspuns,
                "profesor": {
                    "nume": profesor_ales.nume,
                    "materie": profesor_ales.materie
                },
                "statistici": {
                    "tokeni_folositi_azi": stats["daily_tokens"],
                    "procent_utilizare": f"{stats['usage_percentage']:.1f}%",
                    "utilizatori_activi": stats["active_users"]
                }
            }
        
        except Exception as e:
            return {"error": str(e)}
    
    def afiseaza_statistici(self):
        """Afișează statistici sistem"""
        stats = token_monitor.get_stats()
        
        print(f"\n{'='*50}")
        print("STATISTICI SISTEM GRATUIT")
        print(f"{'='*50}")
        print(f"Utilizatori activi: {len(self.utilizatori_activi)}/{self.max_utilizatori}")
        print(f"Tokeni folosiți azi: {stats['daily_tokens']}/{stats['max_daily']}")
        print(f"Procent utilizare: {stats['usage_percentage']:.1f}%")
        print(f"Total cereri: {stats['total_requests']}")
        
        if stats['usage_percentage'] > 80:
            print("🚨 ATENȚIE: Aproape de limita zilnică!")

def demo_gratuit():
    """Demo pentru sistemul gratuit"""
    sistem = SistemEducationalFree()
    
    print("🎓 AI Educational - Versiunea GRATUITĂ\n")
    
    # Test cu utilizatori
    test_users = ["user1", "user2", "user3"]
    test_intrebari = [
        "Cum se calculează aria unui dreptunghi?",
        "Ce sunt numerele prime?",
        "Povestește-mi despre dinozauri"
    ]
    
    for i, user_id in enumerate(test_users):
        print(f"\n--- Test utilizator {user_id} ---")
        
        rezultat = sistem.pune_intrebare(
            user_id=user_id,
            intrebare=test_intrebari[i % len(test_intrebari)],
            scoala_nume="Scoala_Normala",
            clasa=2
        )
        
        if "error" in rezultat:
            print(f"Eroare: {rezultat['error']}")
        else:
            print(f"Profesor: {rezultat['profesor']['nume']}")
            print(f"Răspuns: {rezultat['raspuns'][:200]}...")
            print(f"Statistici: {rezultat['statistici']}")
        
        time.sleep(1)
    
    # Afișează statistici finale
    sistem.afiseaza_statistici()

def meniu_gratuit():
    """Meniu interactiv pentru varianta gratuită"""
    sistem = SistemEducationalFree()
    
    print("🎓 AI Educational - Versiunea GRATUITĂ")
    print(f"Limitat la {sistem.max_utilizatori} utilizatori")
    print("Limitări: 5 întrebări/zi, doar materii principale")
    print("Upgrade la Pro pentru acces complet!\n")
    
    while True:
        print(f"\n{'='*40}")
        print("MENIU GRATUIT")
        print(f"{'='*40}")
        print("1. Pune o întrebare")
        print("2. Afișează statistici")
        print("3. Despre versiunea Pro")
        print("4. Ieși")
        
        alegere = input("\nAlege opțiunea (1-4): ")
        
        if alegere == "1":
            user_id = input("ID utilizator: ")
            
            print("Școli disponibile:")
            print("1. Școala Normală")
            print("2. Școala de Muzică George Enescu")
            
            scoala_alegere = input("Alege școala (1-2): ")
            scoala_nume = "Scoala_Normala" if scoala_alegere == "1" else "Scoala_de_Muzica_George_Enescu"
            
            clasa = int(input("Clasa (0-4): "))
            if clasa not in range(5):
                    print("Clasa trebuie să fie între 0 și 4!")
                    continue
            intrebare = input("Întrebarea ta: ")
            if not intrebare.strip():
                    print("Te rog să scrii o întrebare!")
                    continue
            
            rezultat = sistem.pune_intrebare(user_id, intrebare, scoala_nume, clasa)
            
            profesor = sistem.alege_profesor_simplu(intrebare, clasa)
            if profesor:
                print(f"\n🤖 {profesor.nume} ({profesor.materie}) răspunde:")
                print("-" * 50)
                raspuns = profesor.raspunde_intrebare(intrebare)
                print(raspuns)
            else:
                print("Nu am găsit un profesor pentru această întrebare.")

            if "error" in rezultat:
                print(f"\n❌ {rezultat['error']}")
            else:
                print(f"\n✅ Profesor ales: {rezultat['profesor']['nume']} ({rezultat['profesor']['materie']})")
                print(f"\n📝 Răspuns:\n{rezultat['raspuns']}")
                print(f"\n📊 Statistici: {rezultat['statistici']}")
        
        elif alegere == "2":
            sistem.afiseaza_statistici()
            print("\n📊 LIMITELE TALE:")
            print("• 5 întrebări pe zi")
            print("• Doar materii principale (Română, Matematică)")
            print("• Răspunsuri de maxim 400 cuvinte")
        
        elif alegere == "3":
            demo_gratuit()
            print("\n🚀 VERSIUNEA PRO include:")
            print("• Întrebări nelimitate")
            print("• Toate materiile (17+ materii)")
            print("• Profesori specializați cu AI avansat")
            print("• Răspunsuri detaliate")
            print("• Suport pentru ambele școli")
            print("• Fără reclame")
            print("\n💰 Preț: doar XXX RON/lună")
        
        elif alegere == "4":
            print("La revedere! 👋")
            break
        
        else:
            print("Opțiune invalidă!")

def main_free():
    """Funcția principală pentru versiunea gratuită"""
    print("=== AI EDUCATIONAL - VERSIUNEA GRATUITĂ ===")
    print("Testează gratuit cu 5 întrebări pe zi!")
    
    if not os.getenv('OPENAI_API_KEY'):
        print("EROARE: Nu s-a găsit cheia OpenAI API")
        return
    
def meniu_interactiv_free():

    if __name__ == "__main__":
        try:
            main_free()
            print("Verificare configurare...")
            
            if not Config.DEEPSEEK_API_KEY:
                print("❌ EROARE: Lipsește DEEPSEEK_API_KEY în .env")
                exit(1)
            
            if not Config.CLAUDE_API_KEY:
                print("❌ EROARE: Lipsește CLAUDE_API_KEY în .env")
                exit(1)
            
            print("✅ Configurare completă!")
            
            alegere = input("\n1. Meniu interactiv\n2. Demo automat\nAlege (1-2): ")
            
            if alegere == "1":
                meniu_gratuit()
            else:
                demo_gratuit()
        
        except KeyboardInterrupt:
            print("\n\nProgram întrerupt. La revedere!")
        except Exception as e:
            print(f"\nEroare: {e}")
            logger.error(f"Eroare în main_free(): {e}")