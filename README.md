# Drishti IC  
### Automated Optical Inspection (AOI) for Counterfeit IC Marking Detection  

**Smart India Hackathon 2025**  
**Problem ID:** 25162  
**Theme:** Smart Automation  
**Team:** Win Diesel  
**Category:** Software Edition  

---

## Overview  

**Drishti IC** is an AI-powered platform that automates the authentication and verification of Integrated Circuits (ICs).  
It integrates computer vision, optical character recognition (OCR), and OEM datasheet validation to identify counterfeit components in seconds, ensuring genuine products across the electronics supply chain.

> “Drishti IC – India’s Vision for Counterfeit-Free Electronics.”

The platform performs automated image inspection, text extraction, and cross-referencing against OEM standards to deliver reliable authenticity verification with high precision and throughput.

## Problem Statement  

Counterfeit Integrated Circuits (ICs) have become a serious issue in the global electronics manufacturing and supply chain.  
These fake components lead to unreliable products, financial losses, and safety risks in critical systems such as healthcare, aerospace, and consumer electronics.

Traditional verification methods rely on **manual inspection**, which is:  
- Time-consuming and inconsistent  
- Prone to human error  
- Difficult to scale for high production volumes  

To address this, **Drishti IC** proposes an automated, software-based Optical Inspection (AOI) system that ensures **accurate, repeatable, and high-speed verification** of IC authenticity — all without requiring expensive specialized hardware.

## Proposed Solution  

**Drishti IC** introduces a fully automated system to detect and verify Integrated Circuits through AI-driven image processing and OEM database validation.  
The solution moves beyond manual sampling by enabling fast, consistent, and data-backed quality assurance.

### Key Components  

1. **Full Process Automation**  
   Automates the entire IC verification workflow, eliminating manual steps and inspection subjectivity.  

2. **AI-Driven Detection**  
   Uses a deep learning–based detection model (YOLOv8) and Optical Character Recognition (OCR) to read chip markings accurately, even under varied lighting and orientations.  

3. **Cross-Verification with OEM Standards**  
   Extracted text and logo features are automatically compared against official manufacturer datasheets stored in a centralized repository.  

4. **Reliable Verdict Generation**  
   Produces a confidence score and authenticity status (Genuine / Suspect) with supporting data visualization for traceability.  

5. **Software-Only Deployment**  
   Easily deployable on any standard computing device without additional hardware, enabling rapid scalability and industry adoption.

![Problem Statement 2](https://github.com/user-attachments/assets/0e65016f-78bb-4d2b-bd62-ec4b16aa21cc)


## System Architecture  

The **Drishti IC** system is built on a modular, cloud-ready architecture that integrates a modern web frontend, a high-performance AI backend, and an intelligent inference layer for IC marking verification.

The design ensures scalability, security, and seamless interaction between user interface, AI models, and manufacturer databases.

### Frontend  
- **Framework:** Next.js 15 with App Router  
- **UI Library:** React 19  
- **Styling:** Tailwind CSS 4 with Framer Motion for smooth transitions  
- **Visualization:** Recharts 3 for analytics and performance metrics  
- **Language:** TypeScript 5 for strict type safety  

### Backend  
- **Framework:** FastAPI (Python 3.10+)  
- **Server:** Uvicorn ASGI server for concurrency and speed  
- **AI Model Integration:** Roboflow Inference SDK  
- **OCR Engine:** Google Vision OCR  
- **Configuration:** Managed through `.env` using python-dotenv  

### Flow Diagram  

<img width="1489" height="494" alt="image" src="https://github.com/user-attachments/assets/7558c07d-16bc-4fe9-a34e-f14c1b3fe8b4" />

## User Interface & Demo  

The user interface of **Drishti IC** focuses on clarity, responsiveness, and ease of navigation.  
It is optimized for both desktop and mobile users, with dynamic components and smooth transitions powered by Framer Motion.

---

### Landing Page  

The landing page introduces the platform with a modern gradient background and highlights key manufacturers supported by the verification engine.  
It provides quick access to scanning and documentation features through clear call-to-action buttons.

![Landing Page](https://github.com/user-attachments/assets/21c67635-e814-420f-b7ae-fe1daf3b0b4a)
*Landing page showcasing the introductory section and quick navigation options.*

---

### Scanner Page  

The scanning interface enables users to upload or capture an IC image directly through the browser.  
It includes real-time feedback, displaying the detection process and extracted text as the model runs analysis in the background.

![Scanner Page](https://github.com/user-attachments/assets/889d6d50-c0c3-45b0-b6cd-f6e19df8a080)

*Live scanning interface with detection overlay and text extraction results.*

---

### Dashboard Page  

After verification, users are redirected to the dashboard.  
This page presents detailed analysis results including extracted text, manufacturer details, authenticity verdict, and confidence score.

![Dashboard Detailed Report](https://github.com/user-attachments/assets/f2c2878e-ef4f-42b7-98c0-ee05c9251ebd)
*Dashboard showing confidence breakdown and OEM match comparison.*

---

### Analytics View  

The analytics section lists recent scans, authenticity verdicts, and confidence percentages.  
It provides an overview of all processed ICs for traceability and performance monitoring.

![Dashboard Recent Scans](https://github.com/user-attachments/assets/27fd448a-9d14-4e04-9a3b-342fccb4cdc8)
*Analytics table showing recent verification history and verdicts.*

## Key Features  

**Drishti IC** incorporates advanced AI models, modern web technologies, and automated verification mechanisms to deliver precise and scalable counterfeit detection.

### 1. AI-Based Optical Inspection  
Automated inspection of Integrated Circuits using object detection and OCR to eliminate manual dependencies.

### 2. OEM Datasheet Validation  
Cross-verifies extracted text and logo markings against official manufacturer datasheets to ensure authenticity.

### 3. Real-Time Dashboard  
Provides dynamic analytics including confidence scores, component details, and verdict summaries.

### 4. Browser-Based & Mobile-Responsive  
Runs seamlessly on any device through modern web browsers — no external software or hardware setup required.

### 5. Scalable Architecture  
Cloud-ready modular design allowing deployment across manufacturing facilities or inspection labs.

### 6. Data Traceability  
Maintains inspection logs and confidence metrics for auditability, quality tracking, and process optimization.

### 7. Cross-Platform Compatibility  
Built with portable web technologies (Next.js, FastAPI, TypeScript, and Python) ensuring easy integration and updates.

## Impacts and Benefits  

The deployment of **Drishti IC** provides measurable improvements in accuracy, efficiency, and traceability across the semiconductor inspection process.

| Area | Description |
|------|--------------|
| **Speed and Throughput** | Automates inspection bottlenecks, allowing rapid large-scale verification. |
| **Accuracy and Reliability** | Eliminates human subjectivity, ensuring consistent and repeatable results. |
| **Cost Efficiency** | Reduces rework, scrap, and potential recall losses by early counterfeit detection. |
| **Data-Driven Insights** | Generates traceable analytics for performance monitoring and process optimization. |
| **Scalability** | Software-based architecture allows easy integration into existing production workflows. |
| **Trust and Transparency** | Strengthens confidence within the supply chain by ensuring genuine component sourcing. |


## Feasibility and Viability  

The solution is highly feasible for large-scale industrial adoption due to its lightweight architecture and minimal setup requirements.  
With increasing counterfeit risks in the global electronics market, the demand for automated verification tools like **Drishti IC** continues to rise.

### Technical Feasibility  
- Fully software-based — deployable on standard workstations or inspection lines.  
- Modular architecture allows integration with existing enterprise systems.  
- Uses proven technologies: FastAPI, Next.js, Roboflow, and Google Vision OCR.  

### Market Viability  
- Low-cost, high-impact solution for quality control.  
- Addresses real industry challenges in semiconductor sourcing and reliability.  
- Scalable to different domains such as component testing, e-waste management, and research laboratories.  

### Economic and Operational Advantages  
- Reduces inspection time by up to 80% compared to manual validation.  
- Lowers operational overhead and minimizes quality-related failures.  
- Enables traceable digital records for auditing and compliance.

## Team Win Diesel  

| Member | Department |
|---------|-------------|
| Alfiya Fatima | ISE |
| Ananya Gupta | CSE |
| Chetan R | AIML |
| Kshitij N K | CSE |
| Rishi Chirchi | CSE |
| Yuktha P S | ISE |

## Folder Structure  

```bash
Win_Diesel_2/
│
├── backend/                          # FastAPI backend application
│   ├── app.py                        # API entry point
│   ├── models/                       # Model inference and Roboflow integration scripts
│   ├── requirements.txt              # Backend dependencies
│   └── .env                          # Environment variables (API keys, secrets)
│
├── public/                           # Static assets accessible to the frontend
│   └── images/
│       └── readme_images/            # Images used in README (l1.png, l2.png, l3.png, l4.png, etc.)
│
├── src/                              # Next.js frontend source code
│   ├── app/                          # Application routes (Landing, Scanner, Dashboard)
│   ├── components/                   # Reusable UI components
│   ├── styles/                       # Tailwind CSS configuration and stylesheets
│   ├── utils/                        # Helper functions and service integrations
│   └── types/                        # TypeScript interfaces
│
├── docs/                             # Additional documentation and diagrams
│   ├── architecture_diagram.png
│   ├── methodology_flow.png
│   └── feasibility_chart.png
│
├── README.md                         # Project documentation (this file)
└── package.json                      # Frontend dependencies and scripts
```

## License & Acknowledgment  

Developed as part of the **Smart India Hackathon 2025 (Software Edition)** under the **Smart Automation** theme.  
This project was created by **Team Win Diesel** as an innovative AI-driven solution to combat counterfeit Integrated Circuits through automated optical inspection.

All code, documentation, and visuals included in this repository are intended for **educational and research demonstration purposes only**.  
Use, modification, or redistribution of this project outside the SIH context should properly credit the original contributors.

**© 2025 Team Win Diesel — All Rights Reserved.**
