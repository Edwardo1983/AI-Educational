import logging
import os
import time
from typing import List, Optional

import openai

from .gestor_materiale import get_gestor_materiale
from .profesor import ConfigurariProfesor

logger = logging.getLogger(__name__)
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


class Director:
    """Directorul coordoneaza selectia profesorilor folosind cunostinte pedagogice."""

    def __init__(self, nume: str, scoala, configurari: Optional[ConfigurariProfesor] = None) -> None:
        self.nume = nume
        self.scoala = scoala
        self.configurari = configurari or ConfigurariProfesor(temperature=0.3, model="gpt-5")
        self.istoric_decizii = []
        self.gestor_materiale = get_gestor_materiale()
        self.cunostinte_pedagogice = ""
        self.incarca_materiale_pedagogice()

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
            return profesori_disponibili[0]
        except Exception as exc:
            logger.error("Eroare la alegerea profesorului: %s", exc)
            return profesori_disponibili[0] if profesori_disponibili else None

    def creeaza_prompt_director(self, intrebare: str, clasa_tinta: int, profesori_disponibili: List) -> str:
        profesori_text = ", ".join(f"{p.nume} ({p.materie})" for p in profesori_disponibili)
        cunostinte = self.cunostinte_pedagogice[:2584] if self.cunostinte_pedagogice else ""
        return f"""
        Esti Directorul scolii cu expertiza profunda in pedagogie si psihologia copilului. Analizezi limbajul elevilor si alegi profesorul cel mai potrivit pentru a raspunde nevoilor lor.

        {cunostinte}

        Profesorii disponibili pentru clasa {clasa_tinta}:
        {profesori_text}

        Intrebarea elevului:
        "{intrebare}"

        Returneaza DOAR numele profesorului ideal din lista de mai sus.
        """.strip()
