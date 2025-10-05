import logging
import os
import re
import time
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional

import PyPDF2

logger = logging.getLogger(__name__)


def slugify_text(txt: str) -> str:
    """Normalizeaza textul pentru nume de foldere compatibile."""
    if not txt:
        return ""
    text = unicodedata.normalize("NFKD", txt)
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    replacements = {
        "Arn": "in",
        "Ar": "i",
        "��": "a",
        "A�": "a",
        "ET": "s",
        "E>": "t",
    }
    for old, new in replacements.items():
        text = text.replace(old, new)
    text = re.sub(r"\s+", "_", text)
    text = re.sub(r"[^A-Za-z0-9_\-]", "", text)
    return text.strip("_").strip()


class GestorMateriale:
    """Gestioneaza materialele didactice (PDF-uri) si structura de directoare."""

    def __init__(self, cale_baza: str = "materiale_didactice") -> None:
        self.cale_baza = Path(cale_baza)
        self.cale_baza.mkdir(exist_ok=True)
        self.materiale_incarcate: Dict[str, Path] = {}
        self.cache_pdf: Dict[Path, str] = {}
        self.creeaza_structura_completa()

    def creeaza_structura_completa(self) -> None:
        logger.info("Creez structura completa de foldere...")
        cale_director = self.cale_baza / "director_pedagogie"
        cale_director.mkdir(exist_ok=True)

        scoli_config = {
            "Scoala_Normala": {
                0: [
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna_Engleza",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                1: [
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna_Engleza",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                2: [
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                3: [
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
                4: [
                    "Limba_si_Literatura_Romana",
                    "Matematica",
                    "Limba_moderna",
                    "Stiinte_ale_naturii",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Istorie",
                    "Georgrafie",
                    "Educatie_civica",
                    "Religie",
                ],
            },
            "Scoala_de_Muzica_George_Enescu": {
                0: [
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna_Engleza",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                    "Dezvoltare_personala",
                    "Religie",
                ],
                1: [
                    "Comunicare_in_Limba_Romana",
                    "Matematica_si_Explorarea_mediului",
                    "Limba_moderna_Engleza",
                    "Instrument_principal",
                    "Teorie_Solfegiu_Dicteu",
                    "Muzica_si_Miscare",
                    "Arte_vizuale",
                    "Educatie_fizica",
                ],
                2: [
                    "Limba_si_Literatura_Romana",
                    "Matematica",
                    "Limba_moderna",
                    "Instrument_principal",
                    "Teorie_Solfegiu_Dicteu",
                    "Ansamblu",
                    "Educatie_fizica",
                ],
                3: [
                    "Limba_si_Literatura_Romana",
                    "Matematica",
                    "Limba_moderna",
                    "Stiinte_ale_naturii",
                    "Instrument_principal",
                    "Teorie_Solfegiu_Dicteu",
                    "Ansamblu",
                    "Istorie_muzicala",
                    "Educatie_fizica",
                ],
                4: [
                    "Limba_si_Literatura_Romana",
                    "Matematica",
                    "Limba_moderna",
                    "Stiinte_ale_naturii",
                    "Instrument_principal",
                    "Teorie_Solfegiu_Dicteu",
                    "Ansamblu",
                    "Istorie_muzicala",
                    "Educatie_fizica",
                ],
            },
        }

        for scoala, clase in scoli_config.items():
            cale_scoala = self.cale_baza / slugify_text(scoala)
            for clasa, materii in clase.items():
                cale_clasa = cale_scoala / f"clasa_{clasa}"
                for materie in materii:
                    cale_materie = cale_clasa / slugify_text(materie)
                    cale_prof = cale_materie / "profesor"
                    cale_prof.mkdir(parents=True, exist_ok=True)
        logger.info("✔ Structura completa creata cu succes in: %s", self.cale_baza)

    def gaseste_materiale_profesor(self, scoala: str, clasa: int, materie: str, profesor: str) -> List[Path]:
        cale_profesor = (
            self.cale_baza
            / slugify_text(scoala)
            / f"clasa_{clasa}"
            / slugify_text(materie)
            / slugify_text(profesor)
        )
        if not cale_profesor.exists():
            return []
        return list(cale_profesor.glob("*.pdf"))

    def incarca_pdf_cu_cache(self, cale_pdf: Path) -> Optional[str]:
        if cale_pdf in self.cache_pdf:
            return self.cache_pdf[cale_pdf]
        try:
            with open(cale_pdf, "rb") as file:
                reader = PyPDF2.PdfReader(file)
                content = "".join(page.extract_text() or "" for page in reader.pages)
                self.cache_pdf[cale_pdf] = content
                return content
        except Exception as exc:
            logger.error("Nu s-a putut incarca PDF-ul %s: %s", cale_pdf, exc)
            return None

    def genereaza_raport_materiale(self) -> Path:
        raport = ["\n=== RAPORT MATERIALE DIDACTICE ===\n"]
        total_pdf = 0
        for root, _, files in os.walk(self.cale_baza):
            pdf_files = [f for f in files if f.endswith(".pdf") and f != "README.txt"]
            if pdf_files and "clasa_" in root:
                path_parts = Path(root).parts
                if len(path_parts) >= 4:
                    scoala, clasa, materie, profesor = path_parts[-4:]
                    raport.append(f"- {profesor.replace('_', ' ')} - {materie.replace('_', ' ')} ({clasa})")
                    for pdf_file in pdf_files:
                        raport.append(f"    * {pdf_file}")
                        total_pdf += 1
                    raport.append("")
        raport.append("=== STATISTICI ===")
        raport.append(f"Total fisiere PDF: {total_pdf}")
        raport.append(
            f"Foldere active: {len([d for d in Path(self.cale_baza).rglob('*') if d.is_dir()])}"
        )

        raport_file = self.cale_baza / f"raport_materiale_{time.strftime('%Y%m%d_%H%M%S')}.txt"
        with open(raport_file, "w", encoding="utf-8") as handler:
            handler.write("\n".join(raport))
        logger.info("Raport salvat in: %s", raport_file)
        return raport_file


def get_gestor_materiale(cale_baza: str = "materiale_didactice") -> GestorMateriale:
    if not hasattr(get_gestor_materiale, "_instance"):
        get_gestor_materiale._instance = GestorMateriale(cale_baza)
    return get_gestor_materiale._instance
