<div align="center">

<img src="benefit_bridge_logo.png" alt="Benefit Bridge Logo" width="200">

#Benefit Bridge
### *The Unified Gateway to Essential Support*

[![Version](https://img.shields.io/badge/Version-1.0.0-blue.svg?style=for-the-badge)](https://github.com/SpiceeMILK021/Benefit-Bridge/releases/tag/v1.0.0)
[![Python](https://img.shields.io/badge/Python-3.12.0-green.svg?style=for-the-badge)](https://www.python.org/downloads/release/python-3120/)
[![Platform](https://img.shields.io/badge/Platform-Windows%20%7C%20macOS-lightgrey.svg?style=for-the-badge)](#installation)

**"You're Closer Than You Think"** Benefit Bridge is a high-performance, privacy-first application designed to eliminate the friction between community members and the assistance they deserve.

---

## 💎 The Main Event: Unified Application Drafting
**Stop filling out the same forms over and over.** The core innovation of Benefit Bridge is the **Unified Profile System**. Instead of starting from scratch for every subsidy, you draft a full application profile *once*. The app then cross-references your data against multiple program requirements simultaneously, generating a master brief that serves as a foundation for all your applications.

</div>

---

## 🚀 Key Capabilities

### 📋 Full-Service Document Preparation
* **One-Click Drafting**: Automatically compile household size, income details, and program interests into a structured profile.
* **Local Persistence**: The app saves your progress to a local `benefit_bridge_draft.json` file. Stop today, finish tomorrow—your data never leaves your device.
* **Professional Exports**: Export your full session results to JSON or formatted summaries to share with social workers or navigators.

### 🔍 Intelligence-Driven Screening
* **Multi-Program Evaluation**: Instantly check eligibility for **Child Care, Food Assistance (SNAP), Utility Relief (LIHEAP), Internet Subsidies, and Transportation**.
* **Dynamic "What-If" Modeling**: Use the real-time income slider to see exactly how changes in your monthly earnings affect your benefit eligibility.
* **State-Specific Logic**: Built-in logic for dozens of U.S. states ensures your eligibility estimates are calculated using localized poverty lines and median income data.

### 📍 Intelligent Office Radar
* **Geographic Precision**: Finds the nearest service offices using ZIP code and City coordinate mapping.
* **Integrated Logistics**: View distances and jump directly to Google Maps for navigation with a single click.

---

<div align="center">

## 🛠️ Technical Specifications

| Component | Specification |
| :--- | :--- |
| **Engine** | Python 3.12.0 |
| **GUI** | Custom Modern Tkinter (Dark Mode Optimized) |
| **Security** | 100% On-Device Processing |
| **Persistence** | Lightweight JSON & CSV |

</div>

---

## 📦 Installation & Setup

Benefit Bridge is available as a standalone executable for **Windows** and **macOS**. No Python installation is required to run the released versions.

1.  **Download**: Visit the [Official v1.0.0 Release](https://github.com/SpiceeMILK021/Benefit-Bridge/releases/tag/v1.0.0).
2.  **Run**: 
    * **Windows**: Run the `.exe` file.
    * **macOS**: Open the `.app` package.
    ** a. You will get a warning that says "Apple could not verify 'BenefitBridge' is free of malware that may harm your Mac or compromise your privacy."
    ** <img src="benefit_bridge_logo.png" alt="Benefit Bridge Logo" width="200">
    *    
3.  **Developers**: To run from source, ensure you are using **Python 3.12.0** and install `Pillow` for image support:
    ```bash
    pip install Pillow
    python BenefitBridge.py
    ```

---

## ⌨️ Power User Shortcuts

<div align="center">

| Key | Action |
| :--- | :--- |
| **Ctrl + S** | Instant Save Draft |
| **Ctrl + E** | Export Session to JSON |
| **Ctrl + Q** | Secure Save & Quit |
| **F1** | Comprehensive Help |

</div>

---

<div align="center">

### ⚖️ Disclaimer
*Benefit Bridge provides estimates for preparation purposes only and does not constitute an official eligibility determination. Program rules, income limits, and required documents vary by state and funding year. Always verify requirements with the administering agency.*

</div>
