import os
from dotenv import load_dotenv
import time
import json
from pathlib import Path
from typing import Dict, List, Optional
import logging
from config import Config, token_monitor
from ai_clients import ai_client_manager

from education import (
    GestorMateriale,
    ConfigurariProfesor,
    Director,
    Profesor,
    get_gestor_materiale,
)
# Configurare logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('sistem_educational.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Încarcă variabilele din fișierul .env
load_dotenv()

class ClasaEducationala:
    """
    Reprezintă o clasă educațională cu toți profesorii săi
    """
    def __init__(self, numar_clasa, scoala):
        self.numar_clasa = numar_clasa
        self.scoala = scoala
        self.profesori = {}
        self.diriginte = None
    
    def adauga_profesor(self, profesor):
        """Adaugă un profesor în clasă"""
        self.profesori[profesor.materie] = profesor
        print(f"Profesorul {profesor.nume} a fost adăugat pentru {profesor.materie}")
    
    def seteaza_diriginte(self, nume_profesor):
        """Setează dirigintele clasei"""
        for profesor in self.profesori.values():
            if profesor.nume == nume_profesor:
                self.diriginte = profesor
                print(f"{nume_profesor} a fost setat ca diriginte")
                return
        print(f"Nu s-a găsit profesorul {nume_profesor}")
    
    def afiseaza_profesori(self):
        """Afișează toți profesorii clasei"""
        print(f"\n--- Profesori clasa {self.numar_clasa}, {self.scoala} ---")
        for materie, profesor in self.profesori.items():
            diriginte_marker = " (DIRIGINTE)" if profesor == self.diriginte else ""
            print(f"• {materie}: {profesor.nume}{diriginte_marker}")

class Scoala:
    """
    Reprezintă o școală cu toate clasele și profesorii săi
    """
    def __init__(self, nume, tip="normala"):
        self.nume = nume
        self.tip = tip  # "normala" sau "muzica"
        self.clase = {}
        self.directori = []
    
    def adauga_clasa(self, clasa):
        """Adaugă o clasă în școală"""
        self.clase[clasa.numar_clasa] = clasa
        print(f"Clasa {clasa.numar_clasa} a fost adăugată la {self.nume}")
    
    def adauga_director(self, director):
        """Adaugă un director în școală"""
        self.directori.append(director)
        print(f"Directorul {director.nume} a fost adăugat la {self.nume}")
    
    def afiseaza_structura(self):
        """Afișează structura completă a școlii"""
        print(f"\n{'='*50}")
        print(f"ȘCOALA: {self.nume.upper()} (Tip: {self.tip})")
        print(f"{'='*50}")
        
        for director in self.directori:
            print(f"Director: {director.nume}")
        
        for numar_clasa, clasa in self.clase.items():
            print(f"\n--- CLASA {numar_clasa} ---")
            for materie, profesor in clasa.profesori.items():
                print(f"  {materie}: {profesor.nume} ({profesor.configurari.model})")

def creeaza_configurari_profesor(materie, clasa):
    """
    Funcție helper pentru a crea configurări specifice fiecărei materii și clase
    """     
    configurari_per_materie = {
        # Materii care necesită creativitate și interacțiune complexă
        "Comunicare_in_Limba_Romana": ConfigurariProfesor(
            temperature=0.9,
            model="gpt-5",
            personalitate="prietenos",
            stil_predare="narativ si interactiv",
            tehnici_speciale=["storytelling", "metafore"],
            max_tokens=2584
        ),
        "Limba_si_Literatura_Romana": ConfigurariProfesor(
            temperature=0.9,
            model="gpt-5",
            personalitate="creativ",
            stil_predare="poetic si expresiv",
            tehnici_speciale=["poezie", "interpretare"],
            max_tokens=2584
        ),
        "Matematica_si_Explorarea_mediului": ConfigurariProfesor(
            temperature=0.9,
            model="claude-sonnet-4-5-20250929",
            personalitate="creativ",
            stil_predare="poetic si expresiv",
            tehnici_speciale=["poezie", "interpretare"],
            max_tokens=1597
        ),
        "Matematica": ConfigurariProfesor(
            temperature=0.4,
            model="claude-sonnet-4-5-20250929",
            personalitate="serios",
            stil_predare="precis si analitic",
            tehnici_speciale=["rezolvare probleme", "rationament matematic"],
            max_tokens=1597
        ),
        "Limba_moderna_Engleza": ConfigurariProfesor(
            temperature=0.8,
            model="gpt-5",
            personalitate="prietenos",
            stil_predare="conversational si interactiv",
            tehnici_speciale=["dialoguri", "jocuri de rol"],
            max_tokens=987
        ),
        "Limba_moderna": ConfigurariProfesor(
            temperature=0.8,
            model="gpt-5",
            personalitate="empatic",
            stil_predare="contextual si practic",
            tehnici_speciale=["scenarii reale", "activitati interactive"],
            max_tokens=987
        ),
        "Educatie_fizica": ConfigurariProfesor(
            temperature=0.6,
            model="gpt-5-nano",
            personalitate="energic",
            stil_predare="dinamic si motivational",
            tehnici_speciale=["motivare pozitiva", "competitie sanatoasa"],
            max_tokens=987
        ),
        "Arte_vizuale": ConfigurariProfesor(
            temperature=0.8,
            model="gpt-5",
            personalitate="creativ",
            stil_predare="vizual si experimental",
            tehnici_speciale=["desen intuitiv", "gandire vizuala"],
            max_tokens=1597
        ),      
        "Dezvoltare_personala": ConfigurariProfesor(
            temperature=0.7,
            model="gpt-5",
            personalitate="calm",
            stil_predare="reflectiv si empatic",
            tehnici_speciale=["intrebari socratice", "exercitii mindfulness"],
            max_tokens=2584
        ),
        "Religie": ConfigurariProfesor(
            temperature=0.5,
            model="gpt-5",
            personalitate="calm",
            stil_predare="reflectiv si etic",
            tehnici_speciale=["pilde", "discutii morale"],
            max_tokens=987
        ),
        "Joc_si_Miscare": ConfigurariProfesor(
            temperature=0.8,
            model="gpt-5",
            personalitate="energic",
            stil_predare="auditiv si kinestezic",
            tehnici_speciale=["ritm", "exercitii vocale"],
            max_tokens=987
        ),
        "Muzica_si_Miscare": ConfigurariProfesor(
            temperature=0.9,
            model="gpt-5",
            personalitate="energic",
            stil_predare="ritmic si kinestezic",
            tehnici_speciale=["dans", "coordonare ritmica"],
            max_tokens=1597
        ),
        "Teorie_Solfegiu_Dicteu": ConfigurariProfesor(
            temperature=0.6,
            model="gpt-5",
            personalitate="serios",
            stil_predare="analitic si auditiv",
            tehnici_speciale=["solfegiere", "analiza armonica"],
            max_tokens=1597
        ),                
        "Educatie_civica": ConfigurariProfesor(
            temperature=0.5,
            model="gpt-5",
            personalitate="serios",
            stil_predare="logic si structurat",
            tehnici_speciale=["algoritmi", "gandire computationala"],
            max_tokens=987
        ),
        "Stiinte_ale_naturii": ConfigurariProfesor(
            temperature=0.6,
            model="claude-sonnet-4-5-20250929",
            personalitate="curios",
            stil_predare="investigativ si experimental",
            tehnici_speciale=["experimente practice", "descoperire stiintifica"],
            max_tokens=1597
        ),  
        "Istorie": ConfigurariProfesor(
            temperature=0.7,
            model="gpt-5",
            personalitate="prietenos",
            stil_predare="narativ si captivant",
            tehnici_speciale=["calatorii virtuale", "istorisiri"],
            max_tokens=2584
        ),      
        "Georgrafie": ConfigurariProfesor(
            temperature=0.7,
            model="gpt-5",
            personalitate="explorator",
            stil_predare="documentarist si analitic",
            tehnici_speciale=["calatorii virtuale", "gandire vizuala"],
            max_tokens=2584
        )    
    }   

    # Configurări default dacă materia nu e specificată
    return configurari_per_materie.get(
        materie, 
        ConfigurariProfesor(temperature=0.7, model="gpt-5", personalitate="prietenos")
    )

def creeaza_structura_educationala():
    """
    Creează structura educațională completă cu ambele școli
    """
    # Creăm școlile
    scoala_normala = Scoala("Scoala_Normală", "normala")
    scoala_muzica = Scoala("Scoala_de_Muzica_George_Enescu", "muzica")
    
    # Definim materiile pentru fiecare clasă și tip de școală
    materii_per_clasa = {
        0: {  # Pregătitoare
            "normala": [
                ("Comunicare_in_Limba_Romana", "Prof_Ion_Creanga"),
                ("Matematica_si_Explorarea_mediului", "Prof_Pitagora"),
                ("Limba_moderna_Engleza", "Prof_William_Shakespeare"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Dezvoltare_personala", "Prof_Carl_Jung"),
                ("Religie", "Prof_Arsenie_Boca")
            ],
            "muzica": [
                ("Comunicare_in_Limba_Romana", "Prof_Ion_Creanga"),
                ("Matematica_si_Explorarea_mediului", "Prof_Pitagora"),
                ("Limba_moderna_Engleza", "Prof_William_Shakespeare"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Dezvoltare_personala", "Prof_Carl_Jung"),
                ("Religie", "Prof_Arsenie_Boca")
            ]
        },
        1: {  # Clasa I
            "normala": [
                ("Comunicare_in_Limba_Romana", "Prof_Ion_Creanga"),
                ("Matematica_si_Explorarea_mediului", "Prof_Pitagora"),
                ("Limba_moderna_Engleza", "Prof_William_Shakespeare"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Dezvoltare_personala", "Prof_Carl_Jung"),
                ("Religie", "Prof_Arsenie_Boca")
            ],
            "muzica": [
                ("Comunicare_in_Limba_Romana", "Prof_Ion_Creanga"),
                ("Matematica_si_Explorarea_mediului", "Prof_Pitagora"),
                ("Limba_moderna_Engleza", "Prof_William_Shakespeare"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Teorie_Solfegiu_Dicteu", "Prof_Ennio_Morricone"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Dezvoltare_personala", "Prof_Carl_Jung"),
                ("Religie", "Prof_Arsenie_Boca")
            ]
        },
        2: {  # Clasa a II-a
            "normala": [
                ("Comunicare_in_Limba_Romana", "Prof_Ion_Creanga"),
                ("Matematica_si_Explorarea_mediului", "Prof_Pitagora"),
                ("Limba_moderna", "Prof_Charles_Dickens"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Dezvoltare_personala", "Prof_Carl_Jung"),
                ("Religie", "Prof_Arsenie_Boca")
            ],
            "muzica": [
                ("Comunicare_in_Limba_Romana", "Prof_Ion_Creanga"),
                ("Matematica_si_Explorarea_mediului", "Prof_Pitagora"),
                ("Limba_moderna_Engleza", "Prof_William_Shakespeare"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Teorie_Solfegiu_Dicteu", "Prof_Ennio_Morricone"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Dezvoltare_personala", "Prof_Carl_Jung"),
                ("Religie", "Prof_Arsenie_Boca")
            ]
        },
        3: {  # Clasa a III-a
            "normala": [
                ("Limba_si_Literatura_Romana", "Prof_Mihai_Eminescu"),
                ("Matematica", "Prof_Euclid"),
                ("Limba_moderna", "Prof_Charles_Dickens"),
                ("Stiinte_ale_naturii", "Prof_Albert_Einstein"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_civica", "Prof_Malala_Yousafzai"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Joc_si_Miscare", "Prof_Bruce_Lee"),
                ("Religie", "Prof_Arsenie_Boca")
            ],
            "muzica": [
                ("Limba_si_Literatura_Romana", "Prof_Mihai_Eminescu"),
                ("Matematica", "Prof_Euclid"),
                ("Limba_moderna_Engleza", "Prof_William_Shakespeare"),
                ("Stiinte_ale_naturii", "Prof_Albert_Einstein"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Teorie_Solfegiu_Dicteu", "Prof_Ennio_Morricone"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_civica", "Prof_Malala_Yousafzai"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Joc_si_Miscare", "Prof_Bruce_Lee"),
                ("Religie", "Prof_Arsenie_Boca")
            ]
        },
        4: {  # Clasa a IV-a
            "normala": [
                ("Limba_si_Literatura_Romana", "Prof_Mihai_Eminescu"),
                ("Matematica", "Prof_Euclid"),
                ("Limba_moderna", "Prof_Charles_Dickens"),
                ("Stiinte_ale_naturii", "Prof_Albert_Einstein"),
                ("Istorie", "Prof_Herodot"),
                ("Geografie", "Prof_Jacques_Yves_Cousteau"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Joc_si_Miscare", "Prof_Bruce_Lee"),
                ("Religie", "Prof_Arsenie_Boca")
            ],
            "muzica": [
                ("Limba_si_Literatura_Romana", "Prof_Mihai_Eminescu"),
                ("Matematica", "Prof_Euclid"),
                ("Limba_moderna_Engleza", "Prof_William_Shakespeare"),
                ("Stiinte_ale_naturii", "Prof_Albert_Einstein"),
                ("Istorie", "Prof_Herodot"),
                ("Geografie", "Prof_Jacques_Yves_Cousteau"),
                ("Muzica_si_Miscare", "Prof_Antonio_Vivaldi"),
                ("Teorie_Solfegiu_Dicteu", "Prof_Ennio_Morricone"),
                ("Arte_vizuale", "Prof_Leonardo_da_Vinci"),
                ("Educatie_civica", "Prof_Malala_Yousafzai"),
                ("Educatie_fizica", "Prof_Nadia_Comaneci"),
                ("Joc_si_Miscare", "Prof_Bruce_Lee"),
                ("Religie", "Prof_Arsenie_Boca")
            ]
        }
    }
    
    # Creăm clasele și profesorii pentru ambele școli
    for numar_clasa in range(5):  # Clasele 0-4
        # Școala normală
        clasa_normala = ClasaEducationala(numar_clasa, scoala_normala.nume)
        for materie, nume_profesor in materii_per_clasa[numar_clasa]["normala"]:
            configurari = creeaza_configurari_profesor(materie, numar_clasa)
            profesor = Profesor(nume_profesor, materie, numar_clasa, scoala_normala.nume, configurari)
            clasa_normala.adauga_profesor(profesor)
        scoala_normala.adauga_clasa(clasa_normala)
        
        # Școala de muzică
        clasa_muzica = ClasaEducationala(numar_clasa, scoala_muzica.nume)
        for materie, nume_profesor in materii_per_clasa[numar_clasa]["muzica"]:
            configurari = creeaza_configurari_profesor(materie, numar_clasa)
            profesor = Profesor(nume_profesor, materie, numar_clasa, scoala_muzica.nume, configurari)
            clasa_muzica.adauga_profesor(profesor)
        scoala_muzica.adauga_clasa(clasa_muzica)
    
    # Adăugăm directori
    director_normala = Director("Prof. Dr. Reuven Feuerstein", scoala_normala)
    director_muzica = Director("Prof. Dr. Jean Piaget", scoala_muzica)
    
    scoala_normala.adauga_director(director_normala)
    scoala_muzica.adauga_director(director_muzica)
    
    return scoala_normala, scoala_muzica

def demo_sistem():
    """
    Demonstrație a sistemului educațional complet
    """
    print("=== SISTEM EDUCATIONAL AI AVANSAT ===\n")
    
    # Verificăm cheia API
    if not os.getenv('OPENAI_API_KEY'):
        print("EROARE: Nu s-a găsit cheia OpenAI API în fișierul .env")
        return
    
    # Creăm structura educațională
    scoala_normala, scoala_muzica = creeaza_structura_educationala()
    
    # Afișăm structurile
    scoala_normala.afiseaza_structura()
    scoala_muzica.afiseaza_structura()
    
    # Test cu întrebări specifice
    intrebari_test = [
        {
            "intrebare": "Cum se calculează aria unui pătrat?",
            "scoala": scoala_normala,
            "clasa": 3
        },
        {
            "intrebare": "Ce este do-ul central la pian?",
            "scoala": scoala_muzica,
            "clasa": 1
        },
        {
            "intrebare": "Povestește-mi despre dinozauri",
            "scoala": scoala_normala,
            "clasa": 2
        }
    ]
    
    print(f"\n{'='*60}")
    print("TESTAREA SISTEMULUI CU ÎNTREBĂRI:")
    print(f"{'='*60}")
    
    for i, test in enumerate(intrebari_test, 1):
        print(f"\n--- TEST {i} ---")
        director = test["scoala"].directori[0]
        profesor_ales = director.alege_profesor_pentru_intrebare(
            test["intrebare"], 
            test["clasa"]
        )
        
        if profesor_ales:
            print(f"Școala: {test['scoala'].nume}")
            print(f"Clasa: {test['clasa']}")
            print(f"Întrebare: {test['intrebare']}")
            print(f"Profesor ales: {profesor_ales.nume} ({profesor_ales.materie})")
            
            raspuns = profesor_ales.raspunde_intrebare(test["intrebare"])
            print(f"Răspuns: {raspuns[:233]}...")
            
            # Afișăm detalii despre profesor
            profesor_ales.afiseaza_detalii_profesor()
        
        time.sleep(1)

def meniu_interactiv():
    """
    Meniu interactiv pentru utilizator
    """
    scoala_normala, scoala_muzica = creeaza_structura_educationala()
    
    while True:
        print(f"\n{'='*50}")
        print("MENIU INTERACTIV - SISTEM EDUCATIONAL")
        print(f"{'='*50}")
        print("1. Afișează structura Școala Normală")
        print("2. Afișează structura Școala de Muzică George Enescu")
        print("3. Pune o întrebare (Școala Normală)")
        print("4. Pune o întrebare (Școala de Muzică)")
        print("5. Afișează detalii profesor specific")
        print("6. Rulează demo complet")
        print("7. Ieși")
        
        alegere = input("\nAlege opțiunea (1-7): ")
        
        if alegere == "1":
            scoala_normala.afiseaza_structura()
        elif alegere == "2":
            scoala_muzica.afiseaza_structura()
        elif alegere in ["3", "4"]:
            scoala = scoala_normala if alegere == "3" else scoala_muzica
            print(f"Școala selectată: {scoala.nume}")
            clasa = int(input("Clasa (0-4): "))
            if clasa not in range(5):
                print("Clasa trebuie să fie între 0 și 4!")
                continue
                
            intrebare = input("Întrebarea ta: ")
            
            # Directorul alege profesorul potrivit
            director = scoala.directori[0]
            profesor_ales = director.alege_profesor_pentru_intrebare(intrebare, clasa)
            
            if profesor_ales:
                print(f"\n--- RĂSPUNS ---")
                print(f"Profesor ales: {profesor_ales.nume} ({profesor_ales.materie})")
                raspuns = profesor_ales.raspunde_intrebare(intrebare)
                print(f"Răspuns: {raspuns}")
            else:
                print("Nu s-a găsit un profesor potrivit pentru această întrebare.")
                
        elif alegere == "5":
            # Afișează detalii profesor specific
            print("Alege școala:")
            print("1. Școala Normală")
            print("2. Școala de Muzică")
            scoala_alegere = input("Școala (1-2): ")
            
            if scoala_alegere == "1":
                scoala_selectata = scoala_normala
            elif scoala_alegere == "2":
                scoala_selectata = scoala_muzica
            else:
                print("Alegere invalidă!")
                continue
            
            clasa = int(input("Clasa (0-4): "))
            if clasa not in range(5):
                print("Clasa trebuie să fie între 0 și 4!")
                continue
                
            if clasa in scoala_selectata.clase:
                clasa_obj = scoala_selectata.clase[clasa]
                print(f"\nProfesorii disponibili pentru clasa {clasa}:")
                for i, (materie, profesor) in enumerate(clasa_obj.profesori.items(), 1):
                    print(f"{i}. {profesor.nume} - {materie}")
                
                try:
                    profesor_index = int(input("Alege profesorul (numărul): ")) - 1
                    profesor_ales = list(clasa_obj.profesori.values())[profesor_index]
                    profesor_ales.afiseaza_detalii_profesor()
                except (ValueError, IndexError):
                    print("Alegere invalidă!")
            else:
                print("Clasa nu există!")
                
        elif alegere == "6":
            demo_sistem()
            
        elif alegere == "7":
            print("La revedere!")
            break
            
        else:
            print("Opțiune invalidă! Te rog alege între 1-7.")

def main():
    """
    Funcția principală a aplicației
    """
    print("=== SISTEM EDUCATIONAL AI AVANSAT ===")
    print("Versiunea 1.0 - Dezvoltat pentru școli primare")
    print("Suportă Școala Normală și Școala de Muzică George Enescu")
    print("Cu profesori AI specializați pentru fiecare materie și clasă\n")
    
    # Verificăm dacă avem cheia API
    if not os.getenv('OPENAI_API_KEY'):
        print("EROARE CRITICĂ!")
        print("Nu s-a găsit cheia OpenAI API în fișierul .env")
        print("\nPaşii pentru configurare:")
        print("1. Creează un fișier .env în același folder cu acest script")
        print("2. Adaugă linia: OPENAI_API_KEY=your_api_key_here")
        print("3. Înlocuiește 'your_api_key_here' cu cheia ta OpenAI reală")
        return
    
    print("✓ Cheia OpenAI API a fost detectată")
    print("✓ Sistemul este gata pentru utilizare")
    
    # Întrebăm utilizatorul ce vrea să facă
    while True:
        print("\nCum vrei să începi?")
        print("1. Demo automat (testează sistemul cu întrebări predefinite)")
        print("2. Meniu interactiv (pune întrebări personalizate)")
        print("3. Ieși din program")
        
        alegere_initiala = input("\nAlege opțiunea (1-3): ").strip()
        
        if alegere_initiala == "1":
            print("\n🚀 Lansez demo-ul automat...")
            demo_sistem()
            break
            
        elif alegere_initiala == "2":
            print("\n🎯 Lansez meniul interactiv...")
            meniu_interactiv()
            break
            
        elif alegere_initiala == "3":
            print("👋 La revedere!")
            break
            
        else:
            print("❌ Opțiune invalidă! Te rog alege 1, 2 sau 3.")

def afiseaza_statistici_sistem():
    """
    Funcție bonus pentru afișarea statisticilor sistemului
    """
    scoala_normala, scoala_muzica = creeaza_structura_educationala()
    
    print(f"\n{'='*60}")
    print("STATISTICI SISTEM EDUCATIONAL")
    print(f"{'='*60}")
    
    total_profesori = 0
    total_materii = set()
    
    for scoala in [scoala_normala, scoala_muzica]:
        profesori_scoala = 0
        materii_scoala = set()
        
        print(f"\n--- {scoala.nume.upper()} ---")
        
        for numar_clasa, clasa in scoala.clase.items():
            profesori_clasa = len(clasa.profesori)
            profesori_scoala += profesori_clasa
            
            for materie in clasa.profesori.keys():
                materii_scoala.add(materie)
                total_materii.add(materie)
        
        total_profesori += profesori_scoala
        print(f"Profesori: {profesori_scoala}")
        print(f"Materii distincte: {len(materii_scoala)}")
        print(f"Clase: {len(scoala.clase)}")
        print(f"Directori: {len(scoala.directori)}")
    
    print(f"\n--- TOTAL SISTEM ---")
    print(f"Școli: 2")
    print(f"Total profesori: {total_profesori}")
    print(f"Total materii distincte: {len(total_materii)}")
    print(f"Total clase: {sum(len(s.clase) for s in [scoala_normala, scoala_muzica])}")
    print(f"Modele AI utilizate: GPT-4o, GPT-5-nano")

def test_configurari_avansate():
    """
    Test pentru configurările avansate ale profesorilor
    """
    print(f"\n{'='*50}")
    print("TEST CONFIGURĂRI AVANSATE")
    print(f"{'='*50}")
    
    scoala_normala, scoala_muzica = creeaza_structura_educationala()
    
    # Testăm un profesor de matemată (serios, precisie ridicată)
    profesor_matematica = scoala_normala.clase[3].profesori["Matematică"]
    print(f"\n--- TESTARE: {profesor_matematica.nume} ---")
    print(f"Materie: {profesor_matematica.materie}")
    print(f"Model: {profesor_matematica.configurari.model}")
    print(f"Temperature: {profesor_matematica.configurari.temperature}")
    print(f"Personalitate: {profesor_matematica.configurari.personalitate}")
    
    # Testăm un profesor de muzică (creativ, energie ridicată)
    profesor_instrument = scoala_muzica.clase[2].profesori["Instrument principal"]
    print(f"\n--- TESTARE: {profesor_instrument.nume} ---")
    print(f"Materie: {profesor_instrument.materie}")
    print(f"Model: {profesor_instrument.configurari.model}")
    print(f"Temperature: {profesor_instrument.configurari.temperature}")
    print(f"Personalitate: {profesor_instrument.configurari.personalitate}")

# Executăm programul doar dacă este rulat direct
if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n👋 Program întrerupt de utilizator. La revedere!")
    except Exception as e:
        print(f"\n❌ A apărut o eroare neașteptată: {e}")
        logger.error(f"Eroare în main(): {e}")




