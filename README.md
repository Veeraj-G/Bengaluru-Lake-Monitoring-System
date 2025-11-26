# Bengaluru Lake Monitoring System

**Final Year Engineering Project (Batch I22)** **Topic:** Online Real-time Survey and Monitoring of Water Bodies in Bengaluru.

---

## 📌 Project Overview

This repository contains the source code for the **Phase 1 Implementation** of the lake monitoring system.

The system uses satellite remote sensing (Sentinel-2) to automate the extraction of water quality parameters. It consists of a Python backend that processes satellite imagery and a web-based dashboard for visualization.

### 🚀 Current Features (Phase 1)

- **Backend API (FastAPI):** Serves real-time analysis data.
- **Scientific Engine:**
  - **MNDWI (Modified Normalized Difference Water Index):** For accurate water body masking in urban environments.
  - **NDTI (Normalized Difference Turbidity Index):** For estimating water turbidity levels.
- **Frontend Dashboard:** An interactive HTML/JS interface displaying live metrics (Area, Turbidity, Status).

---

## 🛠️ Installation & Setup

Follow these steps to run the project locally.

### 1. Clone the Repository

```bash
git clone [https://github.com/Veeraj-G/Bengaluru-Lake-Monitoring-System.git](https://github.com/Veeraj-G/Bengaluru-Lake-Monitoring-System.git)
cd Bengaluru-Lake-Monitoring-System


2. Install Dependencies
Ensure you have Python installed. Then run:

Bash
pip install -r requirements.txt

3. ⚠️ Important: Add Satellite Data
Due to file size limits, the satellite imagery is not hosted on GitHub.

Download the file Sentinel2_Hebbal_Lake_2024.tif from the Team Google Drive.

Place the file directly into the root folder of this project (same folder as main.py).

🏃‍♂️ How to Run
Step 1: Start the Backend Server
Open your terminal in the project folder and run:

Bash

uvicorn main:app --reload
You should see a message saying: Application startup complete.

Step 2: Open the Dashboard
Locate the index.html file in the project folder.

Double-click it to open it in your web browser.

The dashboard will automatically connect to the local API and display the analysis.

Project Structure
main.py: The FastAPI server configuration and endpoints.

analyze_hebbal.py: The core scientific script containing the NDTI and MNDWI algorithms.

index.html: The frontend user interface.

requirements.txt: List of required Python libraries (fastapi, rasterio, numpy, etc.).

Note to Contributors: Please do not push large .tif files or the venv folder to this repository. These are ignored by .gitignore.
```
