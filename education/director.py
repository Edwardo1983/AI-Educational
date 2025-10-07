import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

import openai

from ai_clients import ai_client_manager
from .gestor_materiale import get_gestor_materiale
from .profesor import ConfigurariProfesor

logger = logging.getLogger(__name__)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

_PROFILE_FILENAME = "profil_director.json"
_MAX_PROFILE_SOURCE = 4096


class Director:
    """Directorul coordoneaza selectia profesorilor folosind cunostinte pedagogice."""

    def __init__(self, nume: str, scoala, configurari: Optional[ConfigurariProfesor] = None) -> None:
        self.nume = nume
        self.scoala = scoala
        self.configurari = configurari or ConfigurariProfesor(temperature=0.3, model="gpt-5")
        self.istoric_decizii: List[Dict[str, Any]] = []
        self.gestor_materiale = get_gestor_materiale()
        self.cunostinte_pedagogice = ""
        self.profil_pedagogic: Dict[str, Any] = {}
        self.incarca_materiale_pedagogice()
        self.incarca_sau_genereaza_profil()

    def incarca_materiale_pedagogice(self) -> None:
        cale_director = self.gestor_materiale.cale_baza / "director_pedagogie"
        cale_director.mkdir(exist_ok=True)
        materiale = list(cale_director.glob("*.pdf"))
        cunostinte = []
        for material in materiale:
            text = self.gestor_materiale.incarca_pdf_cu_cache(material)
            if text:
                cunostinte.append(f"Din {material.name}: {text[:2584]}...")
        self.cunostinte_pedagogice = "\n\n".join(cunostinte)

    def incarca_sau_genereaza_profil(self) -> None:
        cale_profil = self.gestor_materiale.cale_baza / "director_pedagogie" / _PROFILE_FILENAME
        profil = None
        if cale_profil.exists():
            try:
                profil = json.loads(cale_profil.read_text(encoding="utf-8"))
            except Exception as exc:
                logger.warning("Nu s-a putut citi profilul directorului: %s", exc)
        if profil is None:
            profil = self.genereaza_profil_din_materiale()
            if profil:
                try:
                    cale_profil.write_text(json.dumps(profil, ensure_ascii=False, indent=2), encoding="utf-8")
                except Exception as exc:
                    logger.warning("Nu s-a putut scrie profilul directorului: %s", exc)
        self.profil_pedagogic = profil or {}

    def genereaza_profil_din_materiale(self) -> Optional[Dict[str, Any]]:
        if not self.cunostinte_pedagogice:
            return None
        text_sursa = self.cunostinte_pedagogice[:_MAX_PROFILE_SOURCE]
        prompt = (
            "Rezuma urmatorul continut pedagogic si extrage un profil pentru directorul scolii.\n"
            "Returneaza JSON valid cu cheile: valori (lista de maxim 3 valori),"
            " ton (string), reguli (lista de maxim 3 reguli).\n"
            "Text:\n"
            f"{text_sursa}"
        )
        try:
            response = ai_client_manager.get_ai_response(
                prompt=prompt,
                subject="Pedagogie",
                user_id="director",
                is_free_tier=False,
                max_tokens=384,
                temperature=0.2,
            )
            content = (response or {}).get("content", "").strip()
            if not content:
                return None
            try:
                profil = json.loads(content)
            except json.JSONDecodeError:
                logger.warning("Profilul returnat nu este JSON valid: %s", content[:120])
                return None
            valori = profil.get("valori")
            ton = profil.get("ton")
            reguli = profil.get("reguli")
            if not isinstance(valori, list) or not isinstance(reguli, list):
                return None
            return {
                "valori": [str(v) for v in valori[:3]],
                "ton": str(ton) if ton else "",
                "reguli": [str(r) for r in reguli[:3]],
            }
        except Exception as exc:
            logger.warning("Nu s-a putut genera profilul directorului: %s", exc)
            return None

    def format_profil_pentru_prompt(self) -> str:
        if not self.profil_pedagogic:
            return ""
        valori = self.profil_pedagogic.get("valori") or []
        ton = self.profil_pedagogic.get("ton") or ""
        reguli = self.profil_pedagogic.get("reguli") or []
        linii = ["Valorile directorului: " + (", ".join(valori) if valori else "nespecificate")]
        if ton:
            linii.append(f"Ton recomandat: {ton}")
        if reguli:
            linii.append("Reguli pentru profesori:")
            linii.extend(f"- {regula}" for regula in reguli)
        return "\n".join(linii)

    def _formateaza_istoric(self) -> str:
        if not self.istoric_decizii:
            return ""
        ultimele = self.istoric_decizii[-3:]
        linii = ["Experienta recenta a directorului:"]
        for entry in reversed(ultimele):
            intrebare = entry.get("intrebare", "")[:80]
            linii.append(
                f"- {entry.get('profesor_ales')} pentru clasa {entry.get('clasa')} (intrebarea: {intrebare}...)"
            )
        return "\n".join(linii)

    def alege_profesor_pentru_intrebare(self, intrebare: str, clasa_tinta: int):
        if clasa_tinta not in self.scoala.clase:
            return None
        clasa = self.scoala.clase[clasa_tinta]
        profesori_disponibili = list(clasa.profesori.values())
        if not profesori_disponibili:
            return None

        prompt = self.creeaza_prompt_director(intrebare, clasa_tinta, profesori_disponibili)
        try:
            response = client.chat.completions.create(
                model=self.configurari.model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=144,
                temperature=self.configurari.temperature,
            )
            profesor_ales_nume = response.choices[0].message.content.strip()
            for profesor in profesori_disponibili:
                if profesor.nume.lower() in profesor_ales_nume.lower():
                    self.istoric_decizii.append(
                        {
                            "intrebare": intrebare,
                            "profesor_ales": profesor.nume,
                            "clasa": clasa_tinta,
                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                        }
                    )
                    return profesor
            logger.info("Directorul nu a returnat un nume clar, se foloseste fallback-ul logic.")
        except Exception as exc:
            logger.error("Eroare la alegerea profesorului: %s", exc)

        fallback = self._alege_profesor_fallback(intrebare, profesori_disponibili, clasa_tinta)
        return fallback or profesori_disponibili[0]

    def creeaza_prompt_director(self, intrebare: str, clasa_tinta: int, profesori_disponibili: List) -> str:
        profesori_text = ", ".join(f"{p.nume} ({p.materie})" for p in profesori_disponibili)
        cunostinte = self.cunostinte_pedagogice[:2584] if self.cunostinte_pedagogice else ""
        profil_text = self.format_profil_pentru_prompt()
        istoric_text = self._formateaza_istoric()
        return (
            "Esti Directorul scolii cu expertiza profunda in pedagogie si psihologia copilului.\n"
            "Foloseste ghidul tau profesional pentru a alege profesorul cel mai potrivit.\n\n"
            f"{profil_text}\n\n"
            f"{istoric_text}\n\n"
            "Materiale studiate recent:\n"
            f"{cunostinte}\n\n"
            f"Profesorii disponibili pentru clasa {clasa_tinta}:\n"
            f"{profesori_text}\n\n"
            "Intrebarea elevului:\n"
            f"\"{intrebare}\"\n\n"
            "Returneaza DOAR numele profesorului ideal din lista de mai sus."
        )

    def _alege_profesor_fallback(self, intrebare: str, profesori: List[Any], clasa_tinta: int):
        if not profesori:
            return None
        intrebare_lower = intrebare.lower()
        domenii = {
            "matematica": ["matemat", "numar", "problem", "calcul", "arie", "fract"],
            "romana": ["litera", "povest", "cuvant", "comunicare"],
            "muzica": ["muzic", "sunet", "instrument"],
            "stiinta": ["stiint", "experiment", "natura"],
        }
        scoruri = []
        for profesor in profesori:
            scor = 0
            materie_lower = getattr(profesor, "materie", "").lower()
            if materie_lower:
                if materie_lower in intrebare_lower:
                    scor += 3
                for domeniu, cuvinte in domenii.items():
                    if domeniu in materie_lower and any(cuvant in intrebare_lower for cuvant in cuvinte):
                        scor += 2
            if getattr(profesor, "clasa", None) == clasa_tinta:
                scor += 1
            if getattr(profesor, "cunostinte_din_materiale", ""):
                scor += 1
            if any(entry.get("profesor_ales") == getattr(profesor, "nume", "") for entry in self.istoric_decizii[-5:]):
                scor += 1
            scoruri.append((scor, profesor))
        scoruri.sort(key=lambda item: item[0], reverse=True)
        return scoruri[0][1] if scoruri else None
