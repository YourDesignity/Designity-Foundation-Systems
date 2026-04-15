<div align="center">

  <h1>🚀 Montreal Int. Business Dashboard</h1>
  
  <p>
    <strong>A High-Performance Enterprise Desktop Application</strong>
  </p>

  <p>
    <a href="#-tech-stack">
      <img src="https://img.shields.io/badge/Frontend-React-61DAFB?style=for-the-badge&logo=react&logoColor=black" />
    </a>
    <a href="#-tech-stack">
      <img src="https://img.shields.io/badge/Desktop-Tauri-24C8D8?style=for-the-badge&logo=tauri&logoColor=white" />
    </a>
    <a href="#-tech-stack">
      <img src="https://img.shields.io/badge/Backend-Python-3776AB?style=for-the-badge&logo=python&logoColor=white" />
    </a>
    <a href="#-tech-stack">
      <img src="https://img.shields.io/badge/Database-MongoDB-47A248?style=for-the-badge&logo=mongodb&logoColor=white" />
    </a>
  </p>

  <p>
    <em>Built by <strong>Designity</strong> | Lead Architect: <strong>Nithin</strong></em>
  </p>

</div>

<br />

---

## 📖 Project Overview

**Montreal Int. Business Dashboard** is a next-generation desktop application designed to streamline international business operations. Unlike traditional web apps, this solution leverages **Tauri** to provide a native, lightweight, and secure desktop experience while maintaining the flexibility of web technologies.

This dashboard serves as the central command center for data visualization, resource management, and real-time analytics for Montreal's operations.

### 🌟 Key Features
*   **Hybrid Architecture:** Combines the UI speed of **React** with the raw processing power of **Python**.
*   **Native Performance:** Powered by **Tauri (Rust)**, ensuring the app uses minimal RAM compared to Electron-based apps.
*   **Real-Time Data:** Seamless integration with **MongoDB** for live business intelligence updates.
*   **Secure Backend:** A dedicated Python subprocess handles sensitive logic and database transactions locally.

---

## 🏗 Tech Stack & Architecture

We utilize a **Service-Oriented Architecture (SOA)** wrapped in a desktop shell.

| Component | Technology | Role |
| :--- | :--- | :--- |
| **User Interface** | ![React](https://img.shields.io/badge/-React-black?logo=react&logoColor=61DAFB) | Dynamic, reactive frontend for data visualization. |
| **Desktop Core** | ![Tauri](https://img.shields.io/badge/-Tauri-black?logo=tauri&logoColor=24C8D8) | Handles windowing, native OS menus, and Rust-based security. |
| **Backend Logic** | ![Python](https://img.shields.io/badge/-Python-black?logo=python&logoColor=3776AB) | Processes complex algorithms and handles heavy data lifting. |
| **Database** | ![MongoDB](https://img.shields.io/badge/-MongoDB-black?logo=mongodb&logoColor=47A248) | NoSQL database for flexible and scalable data storage. |

---

## ⚡ Getting Started (Local Development)

Follow these instructions to set up the development environment.

### 1. Prerequisites
Ensure you have the following installed:
*   [Node.js](https://nodejs.org/) (Latest LTS)
*   [Python 3.10+](https://www.python.org/)
*   [Rust](https://www.rust-lang.org/tools/install) (Required for Tauri)
*   [MongoDB Community Server](https://www.mongodb.com/try/download/community)

### 2. Installation

```bash
# Clone the repository
git clone https://github.com/nithinktofficial/MONTREAL.git
cd MONTREAL

# Install Frontend Dependencies
npm install

# Setup Python Backend (Create Virtual Environment)
python -m venv .venv
# Activate: 
# Windows: .venv\Scripts\activate
# Mac/Linux: source .venv/bin/activate

# Install Python Requirements
pip install -r requirements.txt
