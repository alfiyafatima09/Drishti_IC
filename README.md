# Drishti IC


<img width="200" alt="Project Logo" src="https://github.com/user-attachments/assets/91866100-5a2b-440d-8450-3bd5bf19d4e3" align="right" />

### Counterfeit IC Detection Using Marking Verification
**Drishti IC** is an automated system designed to detect counterfeit integrated circuits (ICs) by analyzing IC markings, package characteristics, and manufacturer-specific parameters. The solution focuses on marking-based verification and supports both offline and online operation, making it suitable for secure and restricted environments.

<br />


## Problem Statement
**PS25162 – Counterfeit IC Detection**

Counterfeit ICs introduce serious risks such as system failures, security vulnerabilities, and performance degradation. Manual inspection processes are time-consuming, error-prone, and difficult to scale.  
Drishti IC addresses this challenge by providing an automated and systematic approach to IC authenticity verification.


## Objectives
- Detect counterfeit ICs using marking and package analysis  
- Automate IC verification to reduce manual inspection  
- Support offline operation for secure environments  
- Ensure reliable verification using trusted references  


## Background Study
The development of Drishti IC was guided by:
- Study of IC marking standards and manufacturer documentation  
- Analysis of datasheets and trusted reference platforms:
  - Digi-Key  
  - Mouser  
  - Element14  
  - Texas Instruments and other OEM websites  
- Review of research literature related to counterfeit electronics detection

## Verification Parameters
The system verifies IC authenticity using the following parameters:
- Part Number  
- Manufacturer Identity and Logo  
- Package Type  
- Pin Count  
- Package Dimensions  

## Key Features
- **Fully Offline Counterfeit Detection**  
  Performs complete marking analysis and parameter verification without internet connectivity, enabling deployment in secure and restricted environments.

- **Online Scraping & Datasheet Parsing**  
  Automatically retrieves and structures verified reference images and datasheet parameters from trusted component platforms when internet access is available.

- **Multimodal Analysis Engine**  
  Utilizes computer vision, OCR, and feature-matching techniques to validate IC markings, logos, dimensions, and package characteristics.

## System Workflow
1. IC image acquisition  
2. Image preprocessing  
3. Marking and text extraction  
4. Parameter validation  
5. Offline or online reference comparison  
6. Authenticity result generation  

## Technology Stack
- **Programming Language:** Python  
- **Computer Vision:** OpenCV  
- **Backend:** FastAPI  
- **Desktop Application:** Wails + Go  
- **Vision–Language Model:** Qwen 8B (for multimodal understanding and contextual validation)
- **Data Sources:** Manufacturer datasheets and distributor platforms  

## Team
Developed by **Team Win Diesel** as part of **Smart India Hackathon**.
