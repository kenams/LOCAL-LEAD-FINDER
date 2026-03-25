"""
Netlify preparer service
Prepares files for Netlify deployment
"""
import os
import zipfile
import shutil
from app.core.logging import logger

class NetlifyPreparer:
    """Prepares mockups for Netlify deployment"""

    def __init__(self):
        self.deploy_dir = os.path.join(os.path.dirname(__file__), "..", "..", "exports", "netlify_deploy")
        self.mockups_dir = os.path.join(os.path.dirname(__file__), "..", "..", "exports", "mockups")

    def prepare_for_deployment(self, mockup_path: str, business_name: str) -> str:
        """
        Prepare mockup for Netlify deployment

        Args:
            mockup_path: Path to the generated HTML mockup
            business_name: Name of the business

        Returns:
            Path to prepared zip file
        """
        try:
            # Create deploy directory
            deploy_path = os.path.join(self.deploy_dir, business_name.replace(" ", "_").lower())
            os.makedirs(deploy_path, exist_ok=True)

            # Copy HTML file as index.html
            index_path = os.path.join(deploy_path, "index.html")
            shutil.copy2(mockup_path, index_path)

            # Create a simple _redirects file for SPA (optional)
            redirects_path = os.path.join(deploy_path, "_redirects")
            with open(redirects_path, 'w') as f:
                f.write("/*    /index.html   200\n")

            # Create zip file
            zip_filename = f"{business_name.replace(' ', '_').lower()}_netlify.zip"
            zip_path = os.path.join(self.deploy_dir, zip_filename)

            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(deploy_path):
                    for file in files:
                        file_path = os.path.join(root, file)
                        arcname = os.path.relpath(file_path, deploy_path)
                        zipf.write(file_path, arcname)

            logger.info(f"Prepared Netlify deployment: {zip_path}")
            return zip_path

        except Exception as e:
            logger.error(f"Netlify preparation failed: {e}")
            return ""