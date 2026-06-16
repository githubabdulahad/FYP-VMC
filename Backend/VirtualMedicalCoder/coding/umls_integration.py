"""
coding/umls_integration.py

Fetch ICD-10-CM and CPT codes from UMLS (National Library of Medicine).
Provides accurate, up-to-date medical coding information without needing CSVs.

Setup:
1. Register at https://www.nlm.nih.gov/research/umls/
2. Get API key
3. Set environment variable: UMLS_API_KEY
"""

import os
import requests
import logging
from functools import lru_cache
from typing import Optional

logger = logging.getLogger(__name__)

UMLS_API_KEY = os.getenv("UMLS_API_KEY")
UMLS_BASE_URL = "https://uts-ws.nlm.nih.gov/rest"


class UMLSCodeLookup:
    """Fetch medical codes from UMLS API."""

    @staticmethod
    @lru_cache(maxsize=1000)
    def get_icd10_info(code: str) -> dict | None:
        """
        Look up ICD-10-CM code from UMLS.

        Args:
            code: ICD-10 code (e.g., "N18.31", "N18.3", "R35.0")

        Returns:
            {
                "code": "N18.31",
                "description": "Chronic kidney disease, stage 3a",
                "semantic_type": "T047",  # Disease or Syndrome
                "cui": "C...",  # UMLS Concept Unique ID
            }
            or None if not found
        """
        if not UMLS_API_KEY:
            logger.warning("UMLS_API_KEY not set. Cannot fetch from UMLS.")
            return None

        try:
            params = {
                "apiKey": UMLS_API_KEY,
                "sabs": "ICD10CM",  # ICD-10-CM source
                "returnIdType": "code",
                "pageSize": 1,
            }

            # Query UMLS search endpoint
            response = requests.get(
                f"{UMLS_BASE_URL}/search",
                params={**params, "string": code},
                timeout=5,
            )

            if response.status_code != 200:
                logger.error(f"UMLS API error: {response.status_code} for code {code}")
                return None

            data = response.json()
            results = data.get("result", {}).get("results", [])

            if not results:
                logger.debug(f"No UMLS results for ICD-10 code: {code}")
                return None

            first_result = results[0]
            return {
                "code": code,
                "description": first_result.get("name", "Unknown"),
                "semantic_type": first_result.get("ui", ""),
                "cui": first_result.get("cui", ""),
                "source": "UMLS",
            }

        except requests.RequestException as e:
            logger.error(f"UMLS request failed for {code}: {e}")
            return None

    @staticmethod
    @lru_cache(maxsize=1000)
    def get_cpt_info(code: str) -> dict | None:
        """
        Look up CPT code from UMLS.

        Args:
            code: CPT code (e.g., "99214", "80048")

        Returns:
            {
                "code": "99214",
                "description": "Office or other outpatient visit...",
                "category": "E/M",
            }
            or None if not found
        """
        if not UMLS_API_KEY:
            logger.warning("UMLS_API_KEY not set. Cannot fetch from UMLS.")
            return None

        try:
            params = {
                "apiKey": UMLS_API_KEY,
                "sabs": "CPT",  # CPT source
                "returnIdType": "code",
                "pageSize": 1,
            }

            response = requests.get(
                f"{UMLS_BASE_URL}/search",
                params={**params, "string": code},
                timeout=5,
            )

            if response.status_code != 200:
                logger.error(f"UMLS API error: {response.status_code} for code {code}")
                return None

            data = response.json()
            results = data.get("result", {}).get("results", [])

            if not results:
                logger.debug(f"No UMLS results for CPT code: {code}")
                return None

            first_result = results[0]
            return {
                "code": code,
                "description": first_result.get("name", "Unknown"),
                "cui": first_result.get("cui", ""),
                "source": "UMLS",
            }

        except requests.RequestException as e:
            logger.error(f"UMLS request failed for {code}: {e}")
            return None

    @staticmethod
    def get_icd10_stages(base_code: str) -> list[dict]:
        """
        Get all stage variants of an ICD-10 code (e.g., N18.3 → N18.31, N18.32).

        Args:
            base_code: Base code without stage (e.g., "N18")

        Returns:
            [
                {"code": "N18.31", "description": "Stage 3a", ...},
                {"code": "N18.32", "description": "Stage 3b", ...},
            ]
        """
        if not UMLS_API_KEY:
            return []

        try:
            # Search for codes starting with base
            params = {
                "apiKey": UMLS_API_KEY,
                "sabs": "ICD10CM",
                "returnIdType": "code",
                "pageSize": 100,  # Get all variants
            }

            response = requests.get(
                f"{UMLS_BASE_URL}/search",
                params={**params, "string": base_code},
                timeout=5,
            )

            if response.status_code != 200:
                return []

            data = response.json()
            results = data.get("result", {}).get("results", [])

            variants = []
            for result in results:
                code = result.get("ui", "")
                if code.startswith(base_code):
                    variants.append({
                        "code": code,
                        "description": result.get("name", ""),
                        "cui": result.get("cui", ""),
                    })

            return variants

        except Exception as e:
            logger.error(f"Failed to get variants for {base_code}: {e}")
            return []


class CMSCodeDownloader:
    """Download codes directly from CMS official files."""

    @staticmethod
    def download_icd10_cms() -> list[dict]:
        """
        Download ICD-10-CM codes from CMS official FTP.
        Updated annually for Oct 1.

        Returns:
            [
                {"code": "N18.31", "description": "Chronic kidney disease, stage 3a"},
                ...
            ]

        Note: This is a placeholder. In production, parse CMS files:
        https://www.cms.gov/Medicare/Coding-and-Billing/ICD-10-CM/
        """
        logger.info("CMS ICD-10 download would go here")
        # In practice:
        # 1. Download .zip from CMS
        # 2. Parse .txt or database format
        # 3. Extract code + description + 7th char notes
        # 4. Store in database
        return []

    @staticmethod
    def download_cpt_descriptors() -> list[dict]:
        """
        Get CPT descriptors from CMS RVU files (free, no AMA license needed).

        CMS publishes CPT code descriptions in their RVU reference files,
        which are public and updated annually.

        Returns:
            [
                {"code": "99214", "description": "Office visit, established..."},
                ...
            ]
        """
        logger.info("CMS CPT descriptor download would go here")
        # In practice:
        # 1. Download RVU file from CMS
        # 2. Parse CPT codes + descriptions
        # 3. Store in database
        return []


# Usage example:
if __name__ == "__main__":
    lookup = UMLSCodeLookup()

    # Get single code
    result = lookup.get_icd10_info("N18.31")
    print(f"ICD-10 N18.31: {result}")

    # Get all stage variants
    variants = lookup.get_icd10_stages("N18")
    print(f"CKD stages: {variants}")

    # Get CPT code
    cpt = lookup.get_cpt_info("99214")
    print(f"CPT 99214: {cpt}")
