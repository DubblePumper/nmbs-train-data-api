from setuptools import setup, find_packages

with open("README.md", "r", encoding="utf-8") as fh:
    long_description = fh.read()

setup(
    name="nmbs-train-data-api",
    version="0.1.0",
    author="NMBS Train Data API Team",
    author_email="your.email@example.com",
    description="API for accessing Belgian railways (NMBS/SNCB) real-time train data",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/yourusername/nmbs-train-data-api",
    project_urls={
        "Bug Tracker": "https://github.com/yourusername/nmbs-train-data-api/issues",
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    package_dir={"": "src"},
    packages=find_packages(where="src"),
    python_requires=">=3.7",
    install_requires=[
        "gtfs-realtime-bindings>=1.0.0",
        "protobuf>=3.20.0",
        "beautifulsoup4>=4.10.0",
        "requests>=2.27.0",
        "python-dotenv>=1.0.0",
        "cloudscraper>=1.2.71",
        "schedule>=1.1.0",
        "flask>=2.0.0",
        "flask-cors>=3.0.10",
        "lxml>=4.9.0",  # For better HTML parsing with BeautifulSoup
        "cchardet>=2.1.7",  # For better character encoding detection
    ],
    entry_points={
        "console_scripts": [
            "nmbs-data-service=service:main",
            "nmbs-web-api=run_web_api:main",
        ],
    },
)