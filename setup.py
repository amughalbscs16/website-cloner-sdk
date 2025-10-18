"""Setup script for WordPress Website Cloner"""

from setuptools import setup, find_packages
from pathlib import Path

# Read the README file
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text(encoding="utf-8") if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file, 'r', encoding='utf-8') as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith('#')]

setup(
    name="wordpress-cloner",
    version="2.0.0",
    author="WordPress Cloner Contributors",
    author_email="",
    description="A modern, professional-grade website cloner with Python SDK and Web UI",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/wordpress-cloner",
    project_urls={
        "Bug Reports": "https://github.com/yourusername/wordpress-cloner/issues",
        "Source": "https://github.com/yourusername/wordpress-cloner",
        "Documentation": "https://github.com/yourusername/wordpress-cloner#readme",
    },
    packages=find_packages(exclude=["tests", "tests.*", "examples", "examples.*"]),
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Internet :: WWW/HTTP",
        "Topic :: Software Development :: Testing",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.0.0",
            "pytest-cov>=4.0.0",
            "black>=23.0.0",
            "isort>=5.12.0",
            "flake8>=6.0.0",
            "mypy>=1.0.0",
        ],
        "web": [
            "fastapi>=0.104.0",
            "uvicorn[standard]>=0.24.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "website-cloner=src.main:main",
            "website-cloner-web=run_webui:main",
        ],
    },
    include_package_data=True,
    package_data={
        "src": [
            "web/templates/*.html",
            "web/static/**/*",
        ],
    },
    zip_safe=False,
    keywords="website cloner scraper selenium webdriver wordpress development",
)
