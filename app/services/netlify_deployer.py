"""
Netlify deployment service.
"""
from __future__ import annotations

import re
import tempfile
import time
import zipfile
from pathlib import Path
from typing import Any, Dict
from uuid import uuid4

import requests

from app.core.config import settings
from app.core.logging import logger


class NetlifyDeployer:
    """Deploy generated mockups to Netlify through the REST API."""

    def __init__(self):
        self.api_base = settings.NETLIFY_API_BASE.rstrip("/")
        self.token = settings.NETLIFY_TOKEN.strip()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "Authorization": f"Bearer {self.token}" if self.token else "",
                "User-Agent": settings.USER_AGENT,
            }
        )

    def create_site(self, business_name: str) -> Dict[str, str]:
        """Create a new Netlify site."""
        if not self.token:
            logger.warning("NETLIFY_TOKEN is missing. Netlify deployment skipped.")
            return {
                "status": "pending",
                "site_id": "",
                "url": "",
                "site_name": "",
                "error": "missing_netlify_token",
            }

        payload = {
            "name": self._generate_site_name(business_name),
            "processing_settings": {"html": {"pretty_urls": True}},
        }

        try:
            response = self.session.post(
                f"{self.api_base}/sites",
                json=payload,
                timeout=settings.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            data = response.json()
            site_id = str(data.get("id", ""))
            url = self._extract_public_url(data)

            if not site_id:
                raise ValueError("Netlify site creation returned no site id.")

            logger.info(f"Created Netlify site {site_id} for {business_name}")
            return {
                "status": "success",
                "site_id": site_id,
                "url": url,
                "site_name": str(data.get("name", payload["name"])),
                "error": "",
            }
        except Exception as e:
            logger.error(f"Netlify site creation failed for {business_name}: {e}")
            return {
                "status": "failed",
                "site_id": "",
                "url": "",
                "site_name": "",
                "error": str(e),
            }

    def deploy_site(self, site_id: str, zip_file: str) -> Dict[str, str]:
        """Upload a ZIP archive to an existing Netlify site."""
        if not self.token:
            logger.warning("NETLIFY_TOKEN is missing. Netlify deployment skipped.")
            return {
                "status": "pending",
                "deploy_id": "",
                "site_id": site_id,
                "state": "pending",
                "error": "missing_netlify_token",
            }

        try:
            with open(zip_file, "rb") as archive:
                response = self.session.post(
                    f"{self.api_base}/sites/{site_id}/deploys",
                    data=archive.read(),
                    headers={"Content-Type": "application/zip"},
                    timeout=settings.REQUEST_TIMEOUT,
                )

            response.raise_for_status()
            data = response.json()
            deploy_id = str(data.get("id", ""))
            state = str(data.get("state", ""))

            if not deploy_id:
                raise ValueError("Netlify deploy returned no deploy id.")

            if state != "ready":
                state = self._wait_for_deploy(deploy_id)

            status = "success" if state == "ready" else "failed"
            if status == "success":
                logger.info(f"Netlify deploy {deploy_id} is ready for site {site_id}")
            else:
                logger.error(f"Netlify deploy {deploy_id} ended in state {state} for site {site_id}")

            return {
                "status": status,
                "deploy_id": deploy_id,
                "site_id": site_id,
                "state": state,
                "error": "" if status == "success" else f"deploy_state_{state}",
            }
        except Exception as e:
            logger.error(f"Netlify deploy failed for site {site_id}: {e}")
            return {
                "status": "failed",
                "deploy_id": "",
                "site_id": site_id,
                "state": "failed",
                "error": str(e),
            }

    def deploy_mockup(self, html_path: str, business_name: str) -> Dict[str, str]:
        """Create a site, deploy the mockup and return the public URL."""
        fallback_url = str(Path(html_path).resolve()) if html_path else ""
        html_file = Path(html_path)

        if not html_path or not html_file.exists():
            logger.error(f"Mockup file does not exist: {html_path}")
            return {
                "status": "failed",
                "mockup_status": "failed",
                "site_id": "",
                "deploy_id": "",
                "url": fallback_url,
                "error": "mockup_file_missing",
            }

        site_result = self.create_site(business_name)
        if site_result["status"] == "pending":
            return {
                "status": "pending",
                "mockup_status": "pending",
                "site_id": "",
                "deploy_id": "",
                "url": fallback_url,
                "error": site_result["error"],
            }

        if site_result["status"] != "success":
            return {
                "status": "failed",
                "mockup_status": "failed",
                "site_id": "",
                "deploy_id": "",
                "url": fallback_url,
                "error": site_result["error"],
            }

        try:
            with tempfile.TemporaryDirectory(prefix="leadfinder-netlify-") as temp_dir:
                zip_file = self._prepare_zip_file(html_file, Path(temp_dir))
                deploy_result = self.deploy_site(site_result["site_id"], zip_file)

            if deploy_result["status"] != "success":
                return {
                    "status": "failed",
                    "mockup_status": "failed",
                    "site_id": site_result["site_id"],
                    "deploy_id": deploy_result["deploy_id"],
                    "url": fallback_url,
                    "error": deploy_result["error"],
                }

            public_url = self.get_public_url(site_result["site_id"], site_result["url"])
            return {
                "status": "success",
                "mockup_status": "deployed",
                "site_id": site_result["site_id"],
                "deploy_id": deploy_result["deploy_id"],
                "url": public_url,
                "error": "",
            }
        except Exception as e:
            logger.error(f"Netlify mockup deployment failed for {business_name}: {e}")
            return {
                "status": "failed",
                "mockup_status": "failed",
                "site_id": site_result["site_id"],
                "deploy_id": "",
                "url": fallback_url,
                "error": str(e),
            }

    def get_public_url(self, site_id: str, site_url: str = "") -> str:
        """Get the best public URL for a Netlify site."""
        if site_url:
            normalized_url = self._normalize_public_url(site_url)
            if normalized_url:
                return normalized_url

        if not self.token:
            return site_url

        try:
            response = self.session.get(
                f"{self.api_base}/sites/{site_id}",
                timeout=settings.REQUEST_TIMEOUT,
            )
            response.raise_for_status()
            return self._extract_public_url(response.json())
        except Exception as e:
            logger.warning(f"Could not fetch Netlify public URL for site {site_id}: {e}")
            return self._normalize_public_url(site_url)

    def _prepare_zip_file(self, html_path: Path, temp_dir: Path) -> str:
        """Create a deployable ZIP archive containing index.html."""
        deploy_dir = temp_dir / "site"
        deploy_dir.mkdir(parents=True, exist_ok=True)

        index_path = deploy_dir / "index.html"
        index_path.write_text(html_path.read_text(encoding="utf-8"), encoding="utf-8")

        redirects_path = deploy_dir / "_redirects"
        redirects_path.write_text("/*    /index.html   200\n", encoding="utf-8")

        zip_path = temp_dir / "site.zip"
        with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as archive:
            archive.write(index_path, "index.html")
            archive.write(redirects_path, "_redirects")

        return str(zip_path)

    def _wait_for_deploy(self, deploy_id: str) -> str:
        """Poll Netlify until a deploy reaches a terminal state."""
        terminal_states = {"ready", "error", "failed"}

        for _ in range(settings.NETLIFY_DEPLOY_POLL_ATTEMPTS):
            time.sleep(settings.NETLIFY_DEPLOY_POLL_INTERVAL)
            try:
                response = self.session.get(
                    f"{self.api_base}/deploys/{deploy_id}",
                    timeout=settings.REQUEST_TIMEOUT,
                )
                response.raise_for_status()
                state = str(response.json().get("state", "")).lower()
                if state in terminal_states:
                    return state
            except Exception as e:
                logger.warning(f"Could not poll Netlify deploy {deploy_id}: {e}")

        return "timeout"

    def _extract_public_url(self, data: Dict[str, Any]) -> str:
        """Extract the public site URL from a Netlify API payload."""
        for key in ("ssl_url", "url", "deploy_ssl_url", "site_url"):
            value = str(data.get(key, "") or "").strip()
            normalized = self._normalize_public_url(value)
            if normalized:
                return normalized
        return ""

    def _normalize_public_url(self, url: str) -> str:
        """Normalize Netlify URLs to HTTPS when possible."""
        if not url:
            return ""
        if url.startswith("http://"):
            return "https://" + url.removeprefix("http://")
        return url

    def _generate_site_name(self, business_name: str) -> str:
        """Generate a Netlify-safe site name."""
        slug = re.sub(r"[^a-z0-9-]+", "-", business_name.lower())
        slug = re.sub(r"-{2,}", "-", slug).strip("-")
        slug = slug[:30] if slug else "prospect"
        return f"leadfinder-{slug}-{uuid4().hex[:8]}"
