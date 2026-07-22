import os
import shutil

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATES_DIR = os.path.join(BASE_DIR, "templates_repo")
BUSINESS_DIR = os.path.join(TEMPLATES_DIR, "business")

TEMPLATE_NAMES = ["informative", "portfolio", "landing_page", "ecommerce"]

for name in TEMPLATE_NAMES:
    target_dir = os.path.join(TEMPLATES_DIR, name)
    os.makedirs(target_dir, exist_ok=True)
    for fname in ["index.html", "about.html", "services.html", "contact.html", "faq.html"]:
        src_file = os.path.join(BUSINESS_DIR, fname)
        dst_file = os.path.join(target_dir, fname)
        if os.path.exists(src_file):
            shutil.copyfile(src_file, dst_file)

print("All template directories created successfully!")
