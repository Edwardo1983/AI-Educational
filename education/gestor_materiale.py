import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

import PyPDF2

logger = logging.getLogger(__name__)

_ROMANIAN_REPLACEMENTS = {
    "ă": "a",
    "â": "a",
    "î": "i",
    "ș": "s",
    "ş": "s",
    "ț": "t",
    "ţ": "t",
    "Ă": "A",
    "Â": "A",
    "Î": "I",
    "Ș": "S",
    "Ş": "S",
    "Ț": "T",
    "Ţ": "T",
}


def slugify_text(txt: str) -> str:
    """Create a filesystem friendly slug from the provided text."""
    if not txt:
        return ""
    text = unicodedata.normalize("NFKD", txt)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    for source, target in _ROMANIAN_REPLACEMENTS.items():
        text = text.replace(source, target)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^A-Za-z0-9_\-]", "", text)
    return text.strip("_")


class GestorMateriale:
    """Manage the on-disk teaching material hierarchy and cached PDF excerpts."""

    def __init__(self, cale_baza: str = "materiale_didactice") -> None:
        self.cale_baza = Path(cale_baza)
        self.cale_baza.mkdir(exist_ok=True)
        self.materiale_incarcate: Dict[str, Path] = {}
        self.cache_pdf: Dict[str, str] = {}
        self.creeaza_structura_completa()

    def creeaza_structura_completa(self) -> None:
        """Build the full folder structure for both schools and all subjects."""
        logger.info("Starting full material directory initialisation...")

        # Folderul pentru director
        cale_director = self.cale_baza / "director_pedagogie"
        cale_director.mkdir(exist_ok=True)

        # Structura pentru școli
        scoli_config: Dict[str, Dict[int, List[str]]] = {
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
                    profesor_folder = mapare_profesori.get(materie, "Prof_Necunoscut")
                    cale_profesor = (
                        self.cale_baza
                        / slugify_text(nume_scoala)
                        / f"clasa_{numar_clasa}"
                        / slugify_text(materie)
                        / profesor_folder
                    )
                    cale_profesor.mkdir(parents=True, exist_ok=True)

                    readme_path = cale_profesor / "README.txt"
                    if not readme_path.exists():
                        self._scrie_readme_profesor(readme_path, nume_scoala, numar_clasa, materie, profesor_folder)

        readme_director = cale_director / "README.txt"
        if not readme_director.exists():
            self._scrie_readme_director(readme_director)

        logger.info("Structure created at: %s", self.cale_baza)
        self.afiseaza_structura_creata()

    def _scrie_readme_profesor(self, readme_path: Path, scoala: str, clasa: int, materie: str, profesor: str) -> None:
        template = f"""
FOLDER: {profesor.replace('_', ' ')} - {materie.replace('_', ' ')}
SCOALA: {scoala.replace('_', ' ')}
CLASA: {clasa}

INSTRUCTIUNI:
- Adaugati aici fisierele PDF cu programa si materialele didactice.
- Folositi nume descriptive pentru fisiere (ex. programa_oficiala, manual, activitati_practice).
"""
        readme_path.write_text(template.strip() + "\n", encoding="utf-8")

    def _scrie_readme_director(self, readme_path: Path) -> None:
        template = f"""
FOLDER DIRECTOR PEDAGOGIE - MATERIALE DE FORMARE

SCOP:
- Materiale pentru dezvoltarea profesionala a directorilor.
- Surse pentru imbunatatirea calitatii educationale.
- Ghiduri pentru gestionarea personalului si relatia cu parintii.

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
"""
        readme_path.write_text(template.strip() + "\n", encoding="utf-8")

    def afiseaza_structura_creata(self) -> None:
        print("\n==================== FOLDER STRUCTURE ====================")
        foldere_create = 0
        for root, _, _ in os.walk(self.cale_baza):
            level = root.replace(str(self.cale_baza), "").count(os.sep)
            indent = "  " * level
            folder_name = os.path.basename(root) or self.cale_baza.name
            print(f"{indent}- {folder_name}/")
            if level > 0:
                foldere_create += 1
        print(f"\nTotal directories created: {foldere_create}")

    def gaseste_materiale_profesor(self, scoala: str, clasa: int, materie: str, profesor: str) -> List[Path]:
        scoala_slug = slugify_text(scoala)
        materie_slug = slugify_text(materie)
        paths_to_check = [profesor, slugify_text(profesor)]
        results: List[Path] = []
        for nume in paths_to_check:
            cale_profesor = self.cale_baza / scoala_slug / f"clasa_{clasa}" / materie_slug / nume
            if cale_profesor.exists():
                results = list(cale_profesor.glob("*.pdf"))
                if results:
                    break
        if not results:
            logger.warning("No PDF materials found for %s - %s (class %s)", profesor, materie, clasa)
        return results

    def gaseste_materiale_director(self) -> List[Path]:
        cale_director = self.cale_baza / "director_pedagogie"
        if not cale_director.exists():
            return []
        return list(cale_director.glob("*.pdf"))

    def incarca_pdf_cu_cache(self, cale_pdf: Path) -> Optional[str]:
        key = str(cale_pdf)
        if key in self.cache_pdf:
            return self.cache_pdf[key]
        try:
            with open(cale_pdf, "rb") as handler:
                reader = PyPDF2.PdfReader(handler)
                content = "".join(page.extract_text() or "" for page in reader.pages)
                self.cache_pdf[key] = content
                return content
        except Exception as exc:
            logger.error("Failed to read PDF %s: %s", cale_pdf, exc)
            return None

    def analizeaza_continut_pdf(self, text_pdf: str, nume_fisier: str) -> List[str]:
        categorii = {
            "psihologie": [
                "inteligenta emotionala",
                "dezvoltare cognitiva",
                "comportament pozitiv",
                "empatie",
                "gestionarea emotiilor",
                "inteligenta sociala",
            ],
            "pedagogie": [
                "invatare accelerata",
                "metode interactive",
                "predare inovativa",
                "motivatia elevului",
                "gandire critica",
            ],
            "management": [
                "leadership educational",
                "organizare eficienta",
                "managementul clasei",
                "strategii pedagogice",
                "dezvoltare profesionala",
            ],
            "comunicare": [
                "relatie profesor-elev",
                "comunicare empatica",
                "dialog eficient",
                "colaborare familie-scoala",
                "solutionarea conflictelor",
            ],
        }
        text_lower = text_pdf.lower()
        categorii_gasite = [cat for cat, cuvinte in categorii.items() if any(cuvant in text_lower for cuvant in cuvinte)]
        logger.debug("PDF %s classified into: %s", nume_fisier, categorii_gasite)
        return categorii_gasite

    def genereaza_raport_materiale(self) -> Path:
        lines = ["RAPORT MATERIALE DIDACTICE", f"Generat: {time.strftime('%Y-%m-%d %H:%M:%S')}", ""]
        total_pdf = 0
        for root, _, files in os.walk(self.cale_baza):
            pdf_files = [f for f in files if f.lower().endswith(".pdf") and f != "README.txt"]
            if pdf_files and "clasa_" in root:
                scoala, clasa, materie, profesor = Path(root).parts[-4:]
                lines.append(f"- {profesor.replace('_', ' ')} - {materie.replace('_', ' ')} ({clasa})")
                for pdf_file in pdf_files:
                    lines.append(f"    * {pdf_file}")
                    total_pdf += 1
                lines.append("")
        lines.append("=== STATISTICI ===")
        lines.append(f"Total fisiere PDF: {total_pdf}")
        lines.append(
            f"Foldere active: {len([d for d in self.cale_baza.rglob('*') if d.is_dir()])}"
        )

        raport_file = self.cale_baza / f"raport_materiale_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        raport_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        logger.info("Raport materiale generat in %s", raport_file)
        return raport_file


def get_gestor_materiale(cale_baza: str = "materiale_didactice") -> GestorMateriale:
    if not hasattr(get_gestor_materiale, "_instance"):
        get_gestor_materiale._instance = GestorMateriale(cale_baza)
    return get_gestor_materiale._instance

