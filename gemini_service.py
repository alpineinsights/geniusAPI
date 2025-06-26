import time
import asyncio
import functools
import json
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

Identifier la valeur correspondante dans le document, même si le libellé diffère 

Extraire cette valeur brute, dans l'unité du document (ex. : euros, milliers d'euros, etc.) 

Fournir cette valeur pour les deux derniers exercices disponibles dans le document (ex : N et N-1) 

Utiliser exclusivement les intitulés fournis ci-dessous, même si le libellé dans le document est différent 

 

Format de sortie JSON 

[ 

  { "intitulé": "Capitaux propres", "année": 2023, "valeur": 420000 }, 

  { "intitulé": "Capitaux propres", "année": 2022, "valeur": 415000 }, 

  ... 

] 

  

Chaque intitulé doit apparaître deux fois dans la liste JSON : une fois pour l'exercice N, une fois pour N-1. 

 

Liste unique des intitulés à rechercher 

Bilan – Actif: 

Total de l'actif circulant 

Total des actifs immobilisés (total II) 

Total de l'actif 

Matières premières et marchandises 

Avances et acomptes versés sur commandes 

Créances à clients et comptes rattachés 

Autres créances 

Charges constatées d'avance 

Capital souscrit appelé, non versé 

Disponibilités 

Amortissements cumulés (SEULEMENT année n. Pas n moins 1) 



Bilan – Passif: 

Total du passif 

Total dettes 

Capitaux propres 

Emprunts et dettes auprès des établissements de crédit 

Emprunts et dettes financières divers 

Avances et acomptes reçus sur commandes en cours 

Dettes fournisseurs et comptes rattachés 

Dettes fiscales et sociales 

Autres dettes 

Dettes sur immobilisations et comptes rattachés 

Concours bancaires courants 



Compte de résultat – Produits: 

Chiffre d'affaires net 

Production vendue de biens 

Production vendue de services 

Production stockée 

Production immobilisée 

Produits financiers 

Produits exceptionnels 

Subventions d'exploitation 



Compte de résultat – Charges: 

Achats de marchandises  

Achats de matières premières et autres approvisionnements 

Variation de stock (marchandises) 

Variation de stocks (matières premières) 

Autres achats et charges externes 

Salaires et traitements 

Charges sociales 

Impôts, taxes et versements assimilés 

Intérêts et charges assimilées 

Charges financières 

Charges exceptionnelles 

Dotations d'exploitation 

 

Résultat: 

Résultat net comptable 

Résultat d'exploitation 

Résultat financier 

Résultat courant 

 

A réécrire comme tel dans le json de sortie : 

Loyer (annual rent dans le payload reçu) 

Nom de la société (companyName dans le payload reçu) 

 

Instructions strictes à respecter 

•     Ne jamais modifier les intitulés fournis 

•     Ne pas interpréter ou compléter une donnée absente 

•     Ne pas faire d'analyse ou de commentaire 

•     Ne pas changer ou convertir les unités du document 

•     Si une donnée est absente pour une des deux années, ne pas l'inventer""")
                ]
            )
        ]
        
        generate_content_config = types.GenerateContentConfig(
            temperature=0.1,
            thinking_config=types.ThinkingConfig(
                thinking_budget=8000,
            ),
            response_mime_type="application/json"
        )
        
        logger.info("Starting Gemini financial data extraction from PDF...")
        
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
        
        # Validate JSON structure and provide clean logging
        try:
            # Try to parse the JSON to validate it
            parsed_json = json.loads(response.text)
            
            # Additional validation: check if it's a list with expected structure
            if isinstance(parsed_json, list):
                valid_entries = 0
                for entry in parsed_json[:5]:  # Check first 5 entries
                    if isinstance(entry, dict) and "intitulé" in entry and "année" in entry and "valeur" in entry:
                        valid_entries += 1
                
                if valid_entries > 0:
                    logger.info(f"Gemini returned valid JSON list with {len(parsed_json)} entries")
                else:
                    logger.warning("Gemini JSON entries don't match expected structure")
                    logger.debug(f"Raw response (first 500 chars): {response.text[:500]}")
            else:
                logger.warning("Gemini response is valid JSON but not a list as expected")
                logger.debug(f"Response type: {type(parsed_json)}")
            
        except json.JSONDecodeError as e:
            logger.error(f"Gemini returned invalid JSON: {e}")
            logger.debug(f"Raw Gemini response (first 1000 chars): {response.text[:1000]}")
            
            # Try to extract JSON from the response if it's wrapped in text
            text = response.text.strip()
            
            # Look for JSON array patterns
            start_idx = text.find('[')
            end_idx = text.rfind(']')
            
            if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
                try:
                    json_part = text[start_idx:end_idx + 1]
                    parsed_json = json.loads(json_part)
                    logger.info("Successfully extracted JSON from Gemini response")
                    return json.dumps(parsed_json, ensure_ascii=False)
                except json.JSONDecodeError:
                    logger.error("Could not extract valid JSON from Gemini response")
            
            return f"Error: Gemini returned malformed JSON: {str(e)}"
        
        return response.text

    except Exception as e:
        logger.error(f"Gemini analysis failed: {str(e)}", exc_info=True)
        return f"An error occurred during the Gemini analysis process: {str(e)}" 