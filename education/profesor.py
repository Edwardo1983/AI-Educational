import logging
import time
from typing import Any, Dict, List, Optional

from config import Config
from ai_clients import ai_client_manager

from .gestor_materiale import get_gestor_materiale

logger = logging.getLogger(__name__)


class ConfigurariProfesor:
    """Configuratii specifice fiecarui profesor AI."""

    def __init__(
        self,
        temperature: float = 0.7,
        max_tokens: int = 2584,
        model: str = "gpt-5-nano",
        personalitate: str = "prietenos",
        stil_predare: str = "interactiv",
        tehnici_speciale: Optional[List[str]] = None,
    ) -> None:
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.model = model
        self.personalitate = personalitate
        self.stil_predare = stil_predare
        self.nivel_pacienta = "ridicat"
        self.stil_comunicare = "adaptat_varstei"
        self.tehnici_speciale = tehnici_speciale or []


class Profesor:
    """Reprezinta un profesor AI cu configuratii si materiale asociate."""

    def __init__(
        self,
        nume: str,
        materie: str,
        clasa: int,
        scoala: str,
        configurari: Optional[ConfigurariProfesor] = None,
        gestor_materiale=None,
    ) -> None:
        self.nume = nume
        self.materie = materie
        self.clasa = clasa
        self.scoala = scoala
        self.configurari = configurari or ConfigurariProfesor()
        self.istoric_conversatii: List[Dict[str, Any]] = []
        self.gestor_materiale = gestor_materiale or get_gestor_materiale()
        self.cunostinte_din_materiale = ""
        self.incarca_materiale_didactice()

    def incarca_materiale_didactice(self) -> None:
        materiale = self.gestor_materiale.gaseste_materiale_profesor(
            self.scoala, self.clasa, self.materie, self.nume
        )
        cunostinte = []
        for material in materiale:
            text = self.gestor_materiale.incarca_pdf_cu_cache(material)
            if text:
                cunostinte.append(f"Din {material.name}: {text[:2584]}...")
        self.cunostinte_din_materiale = "\n\n".join(cunostinte)

    def obtine_prompt_personalizat(self, intrebare: str) -> str:
        prompt_personalitate = {
            "prietenos": "Esti profesorul preferat al copiilor, mereu vesel, cald si empatic.",
            "serios": "Esti un profesor respectat, riguros si atent la detalii.",
            "energic": "Esti un profesor plin de viata, entuziast, care inspira elevii sa-si depaseasca limitele.",
            "calm": "Esti profesorul care ofera siguranta emotionala, liniste si rabdare elevilor.",
            "creativ": "Esti profesorul care aduce mereu idei noi, captivante si inovatoare, stimuland imaginatia elevilor.",
        }
        prompt_clasa = {
            0: "Vei folosi un limbaj simplu, povesti captivante si exemple interactive pentru copii de 5-6 ani.",
            1: "Vei explica intr-un mod clar si direct, folosind exemple din viata de zi cu zi pentru copiii de 6-7 ani.",
            2: "Raspunsurile tale vor fi interactive, incurajand curiozitatea copiilor de 7-8 ani, cu explicatii accesibile.",
            3: "Te vei adresa elevilor de 8-9 ani incurajand gandirea critica si argumentarea logica.",
            4: "Vei introduce concepte avansate pentru copiii de 9-10 ani, folosind limbaj matur si provocator.",
        }
        materiale_context = ""
        if self.cunostinte_din_materiale:
            materiale_context = f"\n\nMateriale didactice disponibile:\n{self.cunostinte_din_materiale[:1597]}"
        return f"""
        {prompt_personalitate.get(self.configurari.personalitate, "Esti un profesor remarcabil care inspira elevii").strip()}
        Te numesti {self.nume}, profesor de {self.materie} la {self.scoala}, special pentru clasa {self.clasa}.

        {prompt_clasa.get(self.clasa, "Adapteaza-ti raspunsul pentru varsta elevilor, stimuland imaginatia si gandirea.")}

        Metoda ta de predare este {self.configurari.stil_predare}, bazata pe implicare activa si empatie profunda.
        Nivelul tau de rabdare este {self.configurari.nivel_pacienta}, asigurand ca fiecare elev se simte valoros si ascultat.

        {materiale_context}

        Intrebarea elevului este: "{intrebare}"

        Raspunde intr-un mod captivant, clar si plin de empatie, oferind exemple practice si incurajand curiozitatea.
        """.strip()

    def raspunde_intrebare(self, intrebare: str, user_id: str = "default", is_free_tier: bool = True) -> str:
        prompt = self.obtine_prompt_personalizat(intrebare)
        try:
            if is_free_tier and not Config.FREE_TIER_ENABLED:
                return "Sistemul gratuit este temporar indisponibil. Va rugam sa incercati mai tarziu."

            result = ai_client_manager.get_ai_response(
                prompt=prompt,
                subject=self.materie,
                user_id=user_id,
                is_free_tier=is_free_tier,
                max_tokens=self.configurari.max_tokens,
                temperature=self.configurari.temperature,
            )
            raspuns = result["content"]
            self.istoric_conversatii.append(
                {
                    "intrebare": intrebare,
                    "raspuns": raspuns,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                    "provider": result["provider"],
                    "tokens_used": result["tokens_used"],
                    "from_cache": result.get("from_cache", False),
                    "user_id": user_id,
                    "configurari_folosite": {
                        "model": result["provider"],
                        "temperature": self.configurari.temperature,
                    },
                }
            )
            return raspuns
        except Exception as exc:
            error_msg = f"Eroare la obtinerea raspunsului: {exc}"
            logger.error(error_msg)
            return error_msg

    def afiseaza_detalii_profesor(self) -> None:
        print("\n--- Detalii profesor ---")
        print(f"Nume: {self.nume}")
        print(f"Materie: {self.materie}")
        print(f"Clasa: {self.clasa}")
        print(f"Scoala: {self.scoala}")
        print(f"Model AI: {self.configurari.model}")
        print(f"Temperatura: {self.configurari.temperature}")
        print(f"Personalitate: {self.configurari.personalitate}")
        print(f"Conversatii in istoric: {len(self.istoric_conversatii)}")
