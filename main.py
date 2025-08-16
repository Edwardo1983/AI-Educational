import os  
import openai
from dotenv import load_dotenv
import time
import json
import PyPDF2
from pathlib import Path
from typing import Dict, List, Optional
import logging
import unicodedata
import re
from config import Config, token_monitor
from ai_clients import ai_client_manager

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

# Configurează client-ul OpenAI cu cheia API
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

def slugify_text(txt: str) -> str:
    """
    Convertește un string (cu diacritice, spații, semne) într-un nume de folder compatibil
    folosit în GestorMateriale.creeaza_structura_completa().
    """
    if not txt:
        return ""
    # Normalizează unicode
    t = unicodedata.normalize("NFKD", txt)
    # Elimină diacritice
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    # Înlocuiește semne specifice
    t = t.replace("în", "in").replace("î", "i").replace("ă", "a").replace("â", "a").replace("ș", "s").replace("ț", "t")
    # Spații -> underscore
    t = re.sub(r"\s+", "_", t)
    # Elimină caractere non-filename
    t = re.sub(r"[^A-Za-z0-9_\-]", "", t)
    return t.strip("_").strip()

class ConfigurariProfesor:
    """
    Clasa pentru configurările specifice fiecărui profesor
    """
    def __init__(self, temperature=0.7, max_tokens=2584, model="gpt-3.5-turbo", personalitate="prietenos", stil_predare="interactiv", tehnici_speciale=None):
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model = model
        self.personalitate = personalitate
        self.stil_predare = stil_predare
        self.nivel_pacienta = "ridicat"
        self.stil_comunicare = "adaptat_varstei"
        self.tehnici_speciale = tehnici_speciale or []

class GestorMateriale:
    """
    Clasa îmbunătățită pentru gestionarea materialelor didactice (PDF-uri)
    """
    def __init__(self, cale_baza="materiale_didactice"):
        self.cale_baza = Path(cale_baza)
        self.cale_baza.mkdir(exist_ok=True)
        self.materiale_incarcate = {}
        self.cache_pdf = {}  # Cache pentru PDF-uri procesate
        self.creeaza_structura_completa()
    
    def creeaza_structura_completa(self):
        """Creează întreaga structură de foldere pentru ambele școli"""
        logger.info("Creez structura completă de foldere...")
        
        # Folderul pentru director
        cale_director = self.cale_baza / "director_pedagogie"
        cale_director.mkdir(exist_ok=True)
        
        # Structura pentru școli
        scoli_config = {
            "Scoala_Normala": {
                0: [  # Pregătitoare
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna_Engleza",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                1: [  # Clasa I
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna_Engleza",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                2: [  # Clasa a II-a
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                3: [  # Clasa a III-a
                    "Limba_si_Literatura_Romana",
                    "Matematica",
                    "Limba_moderna",
                    "Stiinte_ale_naturii",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_civica",
                    "Educatie_fizica",
                    "Joc_si_Miscare",
                    "Religie",
                ],
                4: [  # Clasa a IV-a
                    "Limba_si_Literatura_Romana",
                    "Matematica",
                    "Limba_moderna",
                    "Stiinte_ale_naturii",
                    "Istorie",
                    "Geografie",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Joc_si_Miscare",
                    "Religie",
                ]
            },
            "Scoala_de_Muzica_George_Enescu": {
                0: [  # Pregătitoare
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna_Engleza",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                1: [  # Clasa I
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna_Engleza",
                    "Muzica_si_Miscare",
                    "Teorie_Solfegiu_Dicteu",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                2: [  # Clasa a II-a
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna_Engleza",
                    "Muzica_si_Miscare",
                    "Teorie_Solfegiu_Dicteu",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                3: [  # Clasa a III-a
                    "Limba_si_Literatura_Romana",
                    "Matematica",
                    "Limba_moderna_Engleza",
                    "Stiinte_ale_naturii",
                    "Muzica_si_Miscare",
                    "Teorie_Solfegiu_Dicteu",
                    "Arte_vizuale",
                    "Educatie_civica",
                    "Educatie_fizica",
                    "Joc_si_Miscare",
                    "Religie",
                ],
                4: [  # Clasa a IV-a
                    "Limba_si_Literatura_Romana",
                    "Matematica",
                    "Limba_moderna_Engleza",
                    "Stiinte_ale_naturii",
                    "Istorie",
                    "Geografie",
                    "Muzica_si_Miscare",
                    "Teorie_Solfegiu_Dicteu",
                    "Arte_vizuale",
                    "Educatie_civica",
                    "Educatie_fizica",
                    "Joc_si_Miscare",
                    "Religie",
                ]
            }
        }
        
        # Maparea profesori pentru fiecare materie (nume standardizat pentru foldere)
        mapare_profesori = {
            "Comunicare_in_Limba_Romana": "Prof_Ion_Creanga",
            "Matematica_si_Explorarea_mediului": "Prof_Pitagora",
            "Limba_moderna_Engleza": "Prof_William_Shakespeare",
            "Muzica_si_Miscare": "Prof_Antonio_Vivaldi",
            "Arte_vizuale": "Prof_Leonardo_da_Vinci",
            "Educatie_fizica": "Prof_Nadia_Comaneci",
            "Dezvoltare_personala": "Prof_Carl_Jung",
            "Religie": "Prof_Arsenie_Boca",
            "Teorie_Solfegiu_Dicteu": "Prof_Ennio_Morricone",
            "Limba_moderna": "Prof_Charles_Dickens",
            "Limba_si_Literatura_Romana": "Prof_Mihai_Eminescu",
            "Matematica": "Prof_Euclid",
            "Stiinte_ale_naturii": "Prof_Albert_Einstein",
            "Educatie_civica": "Prof_Malala_Yousafzai",
            "Joc_si_Miscare": "Prof_Bruce_Lee",
            "Istorie": "Prof_Herodot",
            "Geografie": "Prof_Jacques_Yves_Cousteau"            
        }
        
        # Creăm folderele pentru fiecare școală, clasă, materie și profesor
        for nume_scoala, clase in scoli_config.items():
            for numar_clasa, materii in clase.items():
                for materie in materii:
                    if materie not in mapare_profesori:
                        logger.warning(f"[ATENȚIE] Nu există profesor definit pentru materia: {materie}")
                    nume_profesor = mapare_profesori.get(materie, "Prof_Necunoscut")
                    cale_profesor = (self.cale_baza / nume_scoala / 
                                   f"clasa_{numar_clasa}" / materie / nume_profesor)
                    cale_profesor.mkdir(parents=True, exist_ok=True)
                    if not any(cale_profesor.glob("*.pdf")):
                        logger.warning(f"[ATENȚIE] Nu există materiale PDF încărcate în: {cale_profesor}")

                    # Creăm un fișier README în fiecare folder de profesor
                    readme_path = cale_profesor / "README.txt"
                    if not readme_path.exists():
                        with open(readme_path, 'w', encoding='utf-8') as f:
                            f.write(f"""
FOLDER: {nume_profesor} - {materie.replace('_', ' ')}
SCOALA: {nume_scoala.replace('_', ' ')}
CLASA: {numar_clasa}

INSTRUCȚIUNI:
- Adaugă aici fișierele PDF cu programa și materialele didactice
- Numele fișierelor trebuie să fie descriptive
- Exemplu de fișiere recomandate:
  * programa_oficiala_{materie.lower()}_clasa_{numar_clasa}.pdf
  * manual_{materie.lower()}_clasa_{numar_clasa}.pdf  
  * activitati_practice_{materie.lower()}.pdf
  * evaluare_si_notare_{materie.lower()}.pdf

GENERATE AUTOMAT DE SISTEM - {time.strftime('%Y-%m-%d %H:%M:%S')}
                            """)
        
        # Creăm README pentru folderul directorului
        readme_director = cale_director / "README.txt"
        if not readme_director.exists():
            with open(readme_director, 'w', encoding='utf-8') as f:
                f.write(f"""
FOLDER DIRECTOR PEDAGOGIE - MATERIALE DE FORMARE

SCOPUL FOLDERULUI:
- Conține materiale pentru dezvoltarea profesională a directorilor
- Surse de informații pentru îmbunătățirea calității educaționale
- Ghiduri pentru gestionarea personalului didactic și relațiilor cu părinții

TIPURI DE MATERIALE RECOMANDATE:

1. PSIHOLOGIA COPILULUI (3-10 ani):
   * dezvoltarea_cognitiva_copii.pdf
   * etapele_dezvoltarii_emotionale.pdf  
   * comportamentul_copiilor_scolari.pdf

2. PEDAGOGIE MODERNĂ:
   * metode_moderne_predare.pdf
   * evaluarea_progresului_scolar.pdf
   * diferentiere_curriculara.pdf

3. LEADERSHIP EDUCAȚIONAL:
   * managementul_unei_scoli.pdf
   * dezvoltarea_echipei_didactice.pdf
   * leadership_transformational.pdf

4. COMUNICARE ȘI RELAȚII:
   * comunicarea_eficienta_cu_parintii.pdf
   * gestionarea_conflictelor_scolare.pdf
   * colaborarea_scoala_familie.pdf

5. TEHNOLOGII EDUCAȚIONALE:
   * integrarea_tehnologiei_in_educatie.pdf
   * ai_in_educatie.pdf
   * platforme_digitale_educationale.pdf

GENERATE AUTOMAT DE SISTEM - {time.strftime('%Y-%m-%d %H:%M:%S')}
                """)
        
        logger.info(f"✓ Structura completă creată cu succes în: {self.cale_baza}")
        self.afiseaza_structura_creata()
    
    def afiseaza_structura_creata(self):
        """Afișează structura de foldere creată"""
        print(f"\n{'='*60}")
        print("STRUCTURA DE FOLDERE CREATĂ")
        print(f"{'='*60}")
        
        foldere_create = 0
        for root, dirs, files in os.walk(self.cale_baza):
            level = root.replace(str(self.cale_baza), '').count(os.sep)
            indent = ' ' * 2 * level
            folder_name = os.path.basename(root)
            if level == 0:
                print(f"📁 {folder_name}/")
            else:
                print(f"{indent}📁 {folder_name}/")
                foldere_create += 1
        
        print(f"\n✓ Total foldere create: {foldere_create}")
        print("✓ Poți adăuga acum PDF-urile în folderele respective!")
    
    def incarca_pdf_cu_cache(self, cale_fisier):
        """Încarcă și extrage textul dintr-un PDF cu sistem de cache"""
        cale_str = str(cale_fisier)
        
        # Verifică cache-ul
        if cale_str in self.cache_pdf:
            logger.info(f"PDF încărcat din cache: {cale_fisier.name}")
            return self.cache_pdf[cale_str]
        
        try:
            with open(cale_fisier, 'rb') as fisier:
                cititor_pdf = PyPDF2.PdfReader(fisier)
                text = ""
                
                for i, pagina in enumerate(cititor_pdf.pages):
                    try:
                        text += pagina.extract_text()
                        text += f"\n--- Pagina {i+1} ---\n"
                    except Exception as e:
                        logger.warning(f"Eroare la pagina {i+1} din {cale_fisier.name}: {e}")
                        continue
                
                # Salvează în cache
                self.cache_pdf[cale_str] = text
                logger.info(f"✓ PDF încărcat și salvat în cache: {cale_fisier.name} ({len(text)} caractere)")
                return text
                
        except Exception as e:
            logger.error(f"Eroare la încărcarea PDF-ului {cale_fisier}: {e}")
            return None
    
    def gaseste_materiale_profesor(self, scoala, clasa, materie, nume_profesor):
        """Găsește toate materialele pentru un profesor specific"""
        scoala_norm = slugify_text(scoala)
        materie_norm = slugify_text(materie)
                
        # 1. Încearcă mai întâi cu numele original (cu spații)
        cale_profesor_original = (self.cale_baza / scoala_norm / f"clasa_{clasa}" / materie_norm / nume_profesor)
        if cale_profesor_original.exists():
            pdf_files = list(cale_profesor_original.glob("*.pdf"))
            if not pdf_files:
                logger.warning(f"[ATENȚIE] Nu există materiale PDF încărcate în: {cale_profesor_original}")
            logger.info(f"Găsite {len(pdf_files)} PDF-uri pentru {nume_profesor} - {materie}")
            return pdf_files

        # 2. Dacă nu există, încearcă și cu numele normalizat (cu underscore, fallback)
        nume_profesor_norm = slugify_text(nume_profesor)
        cale_profesor_norm = (self.cale_baza / scoala_norm / f"clasa_{clasa}" / materie_norm / nume_profesor_norm)
        if cale_profesor_norm.exists():
            pdf_files = list(cale_profesor_norm.glob("*.pdf"))
            if not pdf_files:
                logger.warning(f"[ATENȚIE] Nu există materiale PDF încărcate în: {cale_profesor_norm}")
            logger.info(f"Găsite {len(pdf_files)} PDF-uri pentru {nume_profesor_norm} - {materie}")
            return pdf_files

        # 3. Dacă nu găsește niciuna, avertizează
        logger.warning(f"Nu s-a găsit folderul pentru: {cale_profesor_original} sau {cale_profesor_norm}")
        return []
    
    def gaseste_materiale_director(self):
        """Găsește toate materialele pentru director"""
        cale_director = self.cale_baza / "director_pedagogie"
        if cale_director.exists():
            pdf_files = list(cale_director.glob("*.pdf"))
            logger.info(f"Găsite {len(pdf_files)} PDF-uri pentru director")
            return pdf_files
        return []
    
    def analizeaza_continut_pdf(self, text_pdf, nume_fisier):
        """Analizează și clasifică conținutul unui PDF"""
        cuvinte_cheie = {
            "psihologie": ["inteligență emoțională", "dezvoltare cognitivă", "comportament pozitiv", "empatie", "gestionarea emoțiilor", "inteligență socială"],
            "pedagogie": ["învățare accelerată", "metode interactive", "predare inovativă", "motivația elevului", "gândire critică"],
            "management": ["leadership educațional", "organizare eficientă", "managementul clasei", "strategii pedagogice", "dezvoltare profesională"],
            "comunicare": ["relație profesor-elev", "comunicare empatică", "dialog eficient", "colaborare familie-școală", "soluționarea conflictelor"]
        }
        
        text_lower = text_pdf.lower()
        categorii_gasite = []
        
        for categorie, cuvinte in cuvinte_cheie.items():
            if any(cuvant in text_lower for cuvant in cuvinte):
                categorii_gasite.append(categorie)
        
        return categorii_gasite
    
    def genereaza_raport_materiale(self):
        """Generează un raport cu toate materialele disponibile"""
        raport = f"\n{'='*80}\n"
        raport += "RAPORT MATERIALE DIDACTICE DISPONIBILE\n"
        raport += f"{'='*80}\n"
        raport += f"Generat: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        total_pdf = 0
        
        # Materiale director
        materiale_director = self.gaseste_materiale_director()
        raport += f"📚 MATERIALE DIRECTOR ({len(materiale_director)} fișiere):\n"
        for pdf in materiale_director:
            raport += f"  • {pdf.name}\n"
            total_pdf += 1
        raport += "\n"
        
        # Materiale profesori
        for root, dirs, files in os.walk(self.cale_baza):
            pdf_files = [f for f in files if f.endswith('.pdf') and f != 'README.txt']
            if pdf_files and 'clasa_' in root:
                path_parts = Path(root).parts
                if len(path_parts) >= 4:
                    scoala = path_parts[-4]
                    clasa = path_parts[-3] 
                    materie = path_parts[-2]
                    profesor = path_parts[-1]
                    
                    raport += f"👨‍🏫 {profesor.replace('_', ' ')} - {materie.replace('_', ' ')} ({clasa}):\n"
                    for pdf_file in pdf_files:
                        raport += f"  • {pdf_file}\n"
                        total_pdf += 1
                    raport += "\n"
        
        raport += f"📊 STATISTICI:\n"
        raport += f"  • Total fișiere PDF: {total_pdf}\n"
        raport += f"  • Foldere active: {len([d for d in Path(self.cale_baza).rglob('*') if d.is_dir()])}\n"
        
        # Salvează raportul
        raport_file = self.cale_baza / f"raport_materiale_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(raport_file, 'w', encoding='utf-8') as f:
            f.write(raport)
        
        print(raport)
        logger.info(f"Raport salvat în: {raport_file}")
        return raport_file
gestor_global = GestorMateriale()

class Profesor:
    """
    Clasa Profesor - reprezintă un profesor individual cu specializare și configurări personalizate
    """
    def __init__(self, nume, materie, clasa, scoala, configurari=None):
        self.nume = nume
        self.materie = materie
        self.clasa = clasa
        self.scoala = scoala
        self.configurari = configurari or ConfigurariProfesor()
        self.istoric_conversatii = []
        self.gestor_materiale = gestor_global
        self.cunostinte_din_materiale = ""
        self.incarca_materiale_didactice()
    
    def incarca_materiale_didactice(self):
        """Încarcă materialele didactice ale profesorului"""
        materiale = self.gestor_materiale.gaseste_materiale_profesor(
            self.scoala, self.clasa, self.materie, self.nume
        )
        
        cunostinte = []
        for material in materiale:
            text = self.gestor_materiale.incarca_pdf_cu_cache(material)
            if text:
                cunostinte.append(f"Din {material.name}: {text[:2584]}...")  # Limităm textul
        
        self.cunostinte_din_materiale = "\n\n".join(cunostinte)
    
    def obtine_prompt_personalizat(self, intrebare):
        """Creează un prompt personalizat bazat pe configurările profesorului"""
        prompt_personalitate = {
            "prietenos": "Ești profesorul preferat al copiilor, mereu vesel, cald și empatic.",
            "serios": "Ești un profesor respectat, riguros și atent la detalii.",
            "energic": "Ești un profesor plin de viață, entuziast, care inspiră și motivează elevii să-și depășească limitele.",
            "calm": "Ești profesorul care oferă siguranță emoțională, liniște și răbdare elevilor.",
            "creativ": "Ești profesorul care aduce mereu idei noi, captivante și inovatoare, stimulând imaginația elevilor."
        }
        
        prompt_clasa = {
            0: "Vei folosi un limbaj simplu, povești captivante și exemple interactive adaptate perfect copiilor de 5-6 ani, pentru a le stimula imaginația.",
            1: "Vei explica într-un mod simplu și direct, folosind exemple din viața de zi cu zi pentru copiii de 6-7 ani.",
            2: "Răspunsurile tale vor fi interactive și vor încuraja curiozitatea naturală a copiilor de 7-8 ani, folosind explicații accesibile dar provocatoare.",
            3: "Te vei adresa elevilor de 8-9 ani încurajând gândirea critică, argumentarea logică și curiozitatea intelectuală.",
            4: "Vei introduce concepte avansate pentru copiii de 9-10 ani, folosind limbaj matur, provocator și educativ."
        }
        
        materiale_context = ""
        if self.cunostinte_din_materiale:
            materiale_context = f"\n\nMateriale didactice disponibile:\n{self.cunostinte_din_materiale[:1597]}"
        
        prompt = f"""
        {prompt_personalitate.get(self.configurari.personalitate, "Ești un profesor remarcabil care inspiră elevii")}.
        Te numești {self.nume}, profesor de {self.materie} la {self.scoala}, special pentru clasa {self.clasa}.
        
        {prompt_clasa.get(self.clasa, "Adaptează-ți răspunsul pentru vârsta elevilor, stimulându-le imaginația și gândirea.")}
        
        Metoda ta de predare este {self.configurari.stil_predare}, bazată pe implicare activă și empatie profundă.
        Nivelul tău de răbdare este {self.configurari.nivel_pacienta}, asigurând că fiecare elev se simte valoros și ascultat. 
        
        {materiale_context}
        
        Întrebarea elevului este: "{intrebare}"

        Răspunde într-un mod captivant, clar și plin de empatie, oferind exemple practice, încurajând curiozitatea, entuziasmul și dorința de a descoperi.
        """
        
        return prompt
    
    def raspunde_intrebare(self, intrebare, user_id="default", is_free_tier=True):
        """
        Metoda care trimite o întrebare către OpenAI API cu configurările personalizate
        """
        prompt = self.obtine_prompt_personalizat(intrebare)
        
        try:
                # Verifică dacă sistemul gratuit este activat
            if is_free_tier and not Config.FREE_TIER_ENABLED:
                return "Sistemul gratuit este temporar indisponibil. Vă rugăm să încercați mai târziu."
            
            # Obține răspunsul de la AI
            result = ai_client_manager.get_ai_response(
                prompt=prompt,
                subject=self.materie,
                user_id=user_id,
                is_free_tier=is_free_tier,
                max_tokens=self.configurari.max_tokens,
                temperature=self.configurari.temperature
            )
            
            raspuns = result["content"]
            
            # Salvăm conversația în istoric cu informații suplimentare
            self.istoric_conversatii.append({
                "intrebare": intrebare,
                "raspuns": raspuns,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "provider": result["provider"],
                "tokens_used": result["tokens_used"],
                "from_cache": result.get("from_cache", False),
                "user_id": user_id,
                "configurari_folosite": {
                    "model": result["provider"],
                    "temperature": self.configurari.temperature
                }
            })
            
            return raspuns
        
        except Exception as e:
            error_msg = f"Eroare la obținerea răspunsului: {str(e)}"
            logger.error(error_msg)
            return error_msg
    
    def afiseaza_detalii_profesor(self):
        """Afișează detalii complete despre profesor"""
        print(f"\n--- Detalii profesor ---")
        print(f"Nume: {self.nume}")
        print(f"Materie: {self.materie}")
        print(f"Clasa: {self.clasa}")
        print(f"Școala: {self.scoala}")
        print(f"Model AI: {self.configurari.model}")
        print(f"Temperatură: {self.configurari.temperature}")
        print(f"Personalitate: {self.configurari.personalitate}")
        print(f"Conversații în istoric: {len(self.istoric_conversatii)}")

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

class Director:
    """
    Clasa Director - îmbunătățită cu baza de cunoștințe despre dezvoltarea copiilor
    """
    def __init__(self, nume, scoala, configurari=None):
        self.nume = nume
        self.scoala = scoala
        self.configurari = configurari or ConfigurariProfesor(temperature=0.3, model="gpt-4o")
        self.istoric_decizii = []
        self.gestor_materiale = gestor_global
        self.cunostinte_pedagogice = ""
        self.incarca_materiale_pedagogice()
    
    def incarca_materiale_pedagogice(self):
        """Încarcă materialele despre dezvoltarea copiilor și psihologia educațională"""
        cale_director = self.gestor_materiale.cale_baza / "director_pedagogie"
        cale_director.mkdir(exist_ok=True)
        
        # Căutăm PDF-uri în folderul directorului
        materiale = list(cale_director.glob("*.pdf"))
        cunostinte = []
        
        for material in materiale:
            text = self.gestor_materiale.incarca_pdf_cu_cache(material)
            if text:
                cunostinte.append(f"Din {material.name}: {text[:2584]}...")
        
        self.cunostinte_pedagogice = "\n\n".join(cunostinte)
    
    def alege_profesor_pentru_intrebare(self, intrebare, clasa_tinta):
        """
        Directorul alege profesorul cel mai potrivit pentru o întrebare
        """
        if clasa_tinta not in self.scoala.clase:
            return None
        
        clasa = self.scoala.clase[clasa_tinta]
        profesori_disponibili = list(clasa.profesori.values())
        
        if not profesori_disponibili:
            return None
        
    # Creăm prompt pentru director
    def creeaza_prompt_director(self, intrebare, clasa_tinta, profesori_disponibili):
        prompt = f"""
        Ești Directorul școlii cu expertiză profundă în pedagogie, psihologia copilului și dezvoltare cognitivă. Ai o abilitate excepțională de a analiza limbajul interlocutorului și detecta starea emoțională, identificând rapid patternuri lingvistice pentru a oferi suport educațional optim.

        Scopul tău este să coordonezi eficient profesorii disponibili, alegând profesorul cel mai potrivit să răspundă întrebării sau nevoii exprimate, într-o manieră structurată, clară și educativă. Prioritizezi întotdeauna relația pozitivă profesor-elev și te concentrezi pe stimularea gândirii independente și dezvoltarea capacităților cognitive ale copilului.

        Nu abordezi subiecte nepotrivite pentru mediul școlar (limbaj vulgar, jargon, sex, droguri decât în context educativ clar, muzică nepotrivită vârstei). Răspunsurile tale sunt adaptate riguros vârstei interlocutorului, susținând dezvoltarea armonioasă și încurajând autonomia elevului.

        {self.cunostinte_pedagogice[:2584] if self.cunostinte_pedagogice else ""}

        Profesorii disponibili pentru clasa {clasa_tinta}:
        {', '.join([f'{p.nume} ({p.materie})' for p in profesori_disponibili])}

        Analizează întrebarea sau dialogul:
        "{intrebare}"

        Alege DOAR numele profesorului cel mai potrivit pentru a ajuta copilul să înțeleagă și să-și rezolve singur problema, fără alte explicații.
        """
                
        try:
            response = client.chat.completions.create(
                model=self.configurari.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=144,
                temperature=self.configurari.temperature
            )
            
            profesor_ales_nume = response.choices[0].message.content.strip()
            
            # Găsim profesorul
            for profesor in profesori_disponibili:
                if profesor.nume.lower() in profesor_ales_nume.lower():
                    self.istoric_decizii.append({
                        "intrebare": intrebare,
                        "profesor_ales": profesor.nume,
                        "clasa": clasa_tinta,
                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                    })
                    return profesor
            
            # Dacă nu găsim match exact, returnăm primul
            return profesori_disponibili[0]
            
        except Exception as e:
            logger.error(f"Eroare la alegerea profesorului: {e}")
            return profesori_disponibili[0] if profesori_disponibili else None

def creeaza_configurari_profesor(materie, clasa):
    """
    Funcție helper pentru a crea configurări specifice fiecărei materii și clase
    """     
    configurari_per_materie = {
        # Materii care necesită creativitate și interacțiune complexă
        "Comunicare_in_Limba_Romana": ConfigurariProfesor(
            temperature=0.9,
            model="gpt-4o",
            personalitate="prietenos",
            stil_predare="narativ si interactiv",
            tehnici_speciale=["storytelling", "metafore"],
            max_tokens=2584
        ),
        "Limba_si_Literatura_Romana": ConfigurariProfesor(
            temperature=0.9,
            model="gpt-4o",
            personalitate="creativ",
            stil_predare="poetic si expresiv",
            tehnici_speciale=["poezie", "interpretare"],
            max_tokens=2584
        ),
        "Matematica_si_Explorarea_mediului": ConfigurariProfesor(
            temperature=0.9,
            model="claude-sonnet-4-20250514",
            personalitate="creativ",
            stil_predare="poetic si expresiv",
            tehnici_speciale=["poezie", "interpretare"],
            max_tokens=1597
        ),
        "Matematica": ConfigurariProfesor(
            temperature=0.4,
            model="claude-sonnet-4-20250514",
            personalitate="serios",
            stil_predare="precis si analitic",
            tehnici_speciale=["rezolvare probleme", "rationament matematic"],
            max_tokens=1597
        ),
        "Limba_moderna_Engleza": ConfigurariProfesor(
            temperature=0.8,
            model="gpt-4o",
            personalitate="prietenos",
            stil_predare="conversational si interactiv",
            tehnici_speciale=["dialoguri", "jocuri de rol"],
            max_tokens=987
        ),
        "Limba_moderna": ConfigurariProfesor(
            temperature=0.8,
            model="gpt-4o",
            personalitate="empatic",
            stil_predare="contextual si practic",
            tehnici_speciale=["scenarii reale", "activitati interactive"],
            max_tokens=987
        ),
        "Educatie_fizica": ConfigurariProfesor(
            temperature=0.6,
            model="gpt-3.5-turbo",
            personalitate="energic",
            stil_predare="dinamic si motivational",
            tehnici_speciale=["motivare pozitiva", "competitie sanatoasa"],
            max_tokens=987
        ),
        "Arte_vizuale": ConfigurariProfesor(
            temperature=0.8,
            model="gpt-4o",
            personalitate="creativ",
            stil_predare="vizual si experimental",
            tehnici_speciale=["desen intuitiv", "gandire vizuala"],
            max_tokens=1597
        ),      
        "Dezvoltare_personala": ConfigurariProfesor(
            temperature=0.7,
            model="gpt-4o",
            personalitate="calm",
            stil_predare="reflectiv si empatic",
            tehnici_speciale=["intrebari socratice", "exercitii mindfulness"],
            max_tokens=2584
        ),
        "Religie": ConfigurariProfesor(
            temperature=0.5,
            model="gpt-4o",
            personalitate="calm",
            stil_predare="reflectiv si etic",
            tehnici_speciale=["pilde", "discutii morale"],
            max_tokens=987
        ),
        "Joc_si_Miscare": ConfigurariProfesor(
            temperature=0.8,
            model="gpt-4o",
            personalitate="energic",
            stil_predare="auditiv si kinestezic",
            tehnici_speciale=["ritm", "exercitii vocale"],
            max_tokens=987
        ),
        "Muzica_si_Miscare": ConfigurariProfesor(
            temperature=0.9,
            model="gpt-4o",
            personalitate="energic",
            stil_predare="ritmic si kinestezic",
            tehnici_speciale=["dans", "coordonare ritmica"],
            max_tokens=1597
        ),
        "Teorie_Solfegiu_Dicteu": ConfigurariProfesor(
            temperature=0.6,
            model="gpt-4o",
            personalitate="serios",
            stil_predare="analitic si auditiv",
            tehnici_speciale=["solfegiere", "analiza armonica"],
            max_tokens=1597
        ),                
        "Educatie_civica": ConfigurariProfesor(
            temperature=0.5,
            model="gpt-4o",
            personalitate="serios",
            stil_predare="logic si structurat",
            tehnici_speciale=["algoritmi", "gandire computationala"],
            max_tokens=987
        ),
        "Stiinte_ale_naturii": ConfigurariProfesor(
            temperature=0.6,
            model="claude-sonnet-4-20250514",
            personalitate="curios",
            stil_predare="investigativ si experimental",
            tehnici_speciale=["experimente practice", "descoperire stiintifica"],
            max_tokens=1597
        ),  
        "Istorie": ConfigurariProfesor(
            temperature=0.7,
            model="gpt-4o",
            personalitate="prietenos",
            stil_predare="narativ si captivant",
            tehnici_speciale=["calatorii virtuale", "istorisiri"],
            max_tokens=2584
        ),      
        "Georgrafie": ConfigurariProfesor(
            temperature=0.7,
            model="gpt-4o",
            personalitate="explorator",
            stil_predare="documentarist si analitic",
            tehnici_speciale=["calatorii virtuale", "gandire vizuala"],
            max_tokens=2584
        )    
    }   

    # Configurări default dacă materia nu e specificată
    return configurari_per_materie.get(
        materie, 
        ConfigurariProfesor(temperature=0.7, model="gpt-4o", personalitate="prietenos")
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
    print(f"Modele AI utilizate: GPT-4o, GPT-3.5-turbo")

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