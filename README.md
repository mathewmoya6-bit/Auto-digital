# 🚗 Auto-D Kenya Backend

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat-square&logo=python)](https://python.org)
[![Supabase](https://img.shields.io/badge/Supabase-2.5.3-3ECF8E?style=flat-square&logo=supabase)](https://supabase.com)
[![Render](https://img.shields.io/badge/Render-Deployed-46E3B7?style=flat-square&logo=render)](https://render.com)

**Vehicle cost analysis and valuation system for Kenya.**

Auto-D Kenya provides vehicle valuation, running cost calculation, ownership cost analysis, and M-Pesa payment integration for the Kenyan automotive market.

---

## 📋 Table of Contents

- [Features](#-features)
- [Technology Stack](#-technology-stack)
- [Project Structure](#-project-structure)
- [Installation](#-installation)
- [Configuration](#-configuration)
- [Running the Application](#-running-the-application)
- [API Documentation](#-api-documentation)
- [API Endpoints](#-api-endpoints)
- [M-Pesa Integration](#-mpesa-integration)
- [Scrapers](#-scrapers)
- [Deployment](#-deployment)
- [Testing](#-testing)
- [Contributing](#-contributing)
- [License](#-license)

---

## ✨ Features

### Core Features
- **User Authentication** - JWT-based authentication with Supabase
- **Vehicle Management** - CRUD operations for user vehicles
- **Vehicle Valuation** - AI-powered market value estimation
- **Running Cost Calculator** - Trip cost and 5-year projections
- **Ownership Cost Analysis** - Total cost of ownership with loan amortization
- **M-Pesa Integration** - STK Push payments via Safaricom Daraja API
- **Market Data Scraping** - Automatic scraping from Kenyan marketplaces
- **Report Generation** - PDF and Excel reports

### Technical Features
- ✅ Async/await support for high performance
- ✅ CORS configured for production
- ✅ Comprehensive error handling
- ✅ Structured logging
- ✅ Rate limiting support
- ✅ OpenAPI/Swagger documentation
- ✅ Type hints for better code quality

---

## 🛠 Technology Stack

| Component | Technology |
|-----------|------------|
| **Framework** | FastAPI 0.104.1 |
| **Database** | Supabase (PostgreSQL) |
| **Authentication** | Supabase Auth + JWT |
| **Payment Integration** | Safaricom Daraja API |
| **HTTP Client** | httpx 0.27.2 |
| **Web Scraping** | BeautifulSoup4, lxml, httpx |
| **PDF Generation** | ReportLab 4.2.0 |
| **Excel Generation** | openpyxl |
| **Async Support** | uvicorn + asyncio |
| **Deployment** | Render.com |

---

## 📁 Project Structure
