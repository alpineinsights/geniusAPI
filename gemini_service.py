import time
import asyncio
import functools
from google import genai
from google.genai import types
from logger import logger


async def query_gemini_with_pdf(client: genai.Client, pdf_content: bytes, company_name: str) -> str:
    """Query Gemini 2.5 Flash with PDF content for comprehensive financial ratio calculation"""
    try:
        start_time = time.time()
        
        if not client:
            logger.error("Gemini client not initialized")
            return "Error: Gemini client not initialized"
        
        model = "gemini-2.5-flash"
        contents = [
            types.Content(
                role="user",
                parts=[
                    types.Part.from_bytes(
                        mime_type="application/pdf",
                        data=pdf_content
                    ),
                    types.Part.from_text(text="""Tu es un agent d'extraction de données financières. Le document fourni contient un bilan, un compte de résultat, et éventuellement des annexes d'une entreprise.

Objectif
Pour chaque intitulé standardisé ci-dessous, tu dois :
•	Identifier la valeur correspondante dans le document, même si le libellé diffère
•	Extraire cette valeur brute, dans l'unité du document (ex. : euros, milliers d'euros, etc.)
•	Fournir cette valeur pour les deux derniers exercices disponibles dans le document (ex : N et N-1)
•	Utiliser exclusivement les intitulés fournis ci-dessous, même si le libellé dans le document est différent

Format de sortie JSON
[
  { "intitulé": "Capitaux propres", "année": 2023, "valeur": 420000 },
  { "intitulé": "Capitaux propres", "année": 2022, "valeur": 415000 },
  ...
]
 
Chaque intitulé doit apparaître deux fois dans la liste JSON : une fois pour l'exercice N, une fois pour N-1.

Liste unique des intitulés à rechercher
Bilan – Actif:
•	Total de l'actif circulant
•	Total des actifs immobilisés (total II)
•	Total de l'actif
•	Matières premières et marchandises
•	Avances et acomptes versés sur commandes
•	Créances à clients et comptes rattachés
•	Autres créances
•	Charges constatées d'avance
•	Capital souscrit appelé, non versé
•	Disponibilités

Bilan – Passif:
•	Total du passif
•	Total dettes
•	Capitaux propres
•	Amortissements cumulés
•	Emprunts et dettes auprès des établissements de crédit
•	Emprunts et dettes financières divers
•	Avances et acomptes reçus sur commandes en cours
•	Dettes fournisseurs et comptes rattachés
•	Dettes fiscales et sociales
•	Autres dettes
•	Dettes sur immobilisations et comptes rattachés
•	Concours bancaires courants

Compte de résultat – Produits:
•	Chiffre d'affaires net
•	Production vendue de biens
•	Production vendue de services
•	Production stockée
•	Production immobilisée
•	Produits financiers
•	Produits exceptionnels
•	Subventions d'exploitation

Compte de résultat – Charges:
•	Achats de marchandises 
•	Achats de matières premières et autres approvisionnements
•	Variation de stock (marchandises)
•	Variation de stocks (matières premières)
•	Autres achats et charges externes
•	Salaires et traitements
•	Charges sociales
•	Impôts, taxes et versements assimilés
•	Intérêts et charges assimilées
•	Charges financières
•	Charges exceptionnelles
•	Dotations d'exploitation

Résultat:
•	Résultat net comptable

Instructions strictes à respecter
•	Ne jamais modifier les intitulés fournis
•	Ne pas interpréter ou compléter une donnée absente
•	Ne pas faire d'analyse ou de commentaire
•	Ne pas changer ou convertir les unités du document
•	Si une donnée est absente pour une des deux années, ne pas l'inventer""")
                ]
            )
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=0.1,
            thinking_config=types.ThinkingConfig(
                thinking_budget=8000,
            ),
            response_mime_type="application/json",
            response_schema=genai.types.Schema(
                type=genai.types.Type.OBJECT,
                properties={
                    "Total de l'actif circulant N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Total de l'actif circulant N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Total des actifs immobilisés (total II) N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Total des actifs immobilisés (total II) N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Total de l'actif N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Total de l'actif N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Matières premières et marchandises N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Matières premières et marchandises N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Avances et acomptes versés sur commandes N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Avances et acomptes versés sur commandes N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Créances à clients et comptes rattachés N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Créances à clients et comptes rattachés N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Autres créances N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Autres créances N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Charges constatées d'avance N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Charges constatées d'avance N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Capital souscrit appelé, non versé N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Capital souscrit appelé, non versé N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Disponibilités N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Disponibilités N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Total du passif N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Total du passif N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Total dettes N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Total dettes N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Capitaux propres N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Capitaux propres N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Amortissements cumulés N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Amortissements cumulés N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Emprunts et dettes auprès des établissements de crédit N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Emprunts et dettes auprès des établissements de crédit N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Emprunts et dettes financières divers N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Emprunts et dettes financières divers N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Avances et acomptes reçus sur commandes en cours N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Avances et acomptes reçus sur commandes en cours N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Dettes fournisseurs et comptes rattachés N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Dettes fournisseurs et comptes rattachés N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Dettes fiscales et sociales N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Dettes fiscales et sociales N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Autres dettes N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Autres dettes N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Dettes sur immobilisations et comptes rattachés N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Dettes sur immobilisations et comptes rattachés N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Concours bancaires courants N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Concours bancaires courants N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Chiffre d'affaires net N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Chiffre d'affaires net N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Production vendue de biens N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Production vendue de biens N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Production vendue de services N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Production vendue de services N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Production stockée N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Production stockée N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Production immobilisée N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Production immobilisée N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Produits financiers N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Produits financiers N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Produits exceptionnels N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Produits exceptionnels N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Subventions d'exploitation N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Subventions d'exploitation N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Achats de marchandises N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Achats de marchandises N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Achats de matières premières et autres approvisionnements N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Achats de matières premières et autres approvisionnements N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Variation de stock (marchandises) N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Variation de stock (marchandises) N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Variation de stock (matières premières) N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Variation de stock (matières premières) N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Autres achats et charges externes N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Autres achats et charges externes N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Salaires et traitements N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Salaires et traitements N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Charges sociales N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Charges sociales N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Impôts, taxes et versements assimilés N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Impôts, taxes et versements assimilés N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Intérêts et charges assimilées N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Intérêts et charges assimilées N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Charges financières N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Charges financières N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Charges exceptionnelles N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Charges exceptionnelles N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Dotations d'exploitation N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Dotations d'exploitation N-1": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Résultat net comptable N": genai.types.Schema(type=genai.types.Type.NUMBER),
                    "Résultat net comptable N-1": genai.types.Schema(type=genai.types.Type.NUMBER)
                },
            ),
        )
        
        logger.info("Starting Gemini analysis with comprehensive ratio calculation...")
        
        loop = asyncio.get_running_loop()
        generate_func = functools.partial(
            client.models.generate_content,
            model=model,
            contents=contents,
            config=generate_content_config
        )
        
        response = await loop.run_in_executor(None, generate_func)
        
        total_time = time.time() - start_time
        logger.info(f"Gemini completed in {total_time:.2f}s")
        
        if not response or not response.text:
            logger.error("Gemini returned empty response")
            return "Error: Received an empty response from Gemini."
        
        # Log Gemini output in clean ASCII format
        try:
            gemini_output_clean = response.text.encode('ascii', 'replace').decode('ascii')
            logger.info("=== GEMINI OUTPUT ===")
            logger.info(gemini_output_clean)
            logger.info("=== END GEMINI OUTPUT ===")
        except Exception:
            logger.warning("Could not log Gemini output in ASCII format")
        
        return response.text

    except Exception as e:
        logger.error(f"Gemini analysis failed: {str(e)}")
        return f"An error occurred during the Gemini analysis process: {str(e)}" 